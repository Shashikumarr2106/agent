"""CSV Ingestion and Schema Detection Service."""
import csv
import io
import re
import uuid
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from ..models.dataset import DatasetSchema, ColumnInfo, DatasetUploadResponse
from .database import db_service

def infer_column_type(values: List[str]) -> str:
    """Infer column type (numeric, datetime, boolean, text) from non-empty sample strings."""
    non_empty = [v.strip() for v in values if v is not None and str(v).strip() != ""]
    if not non_empty:
        return "text"

    # Check boolean
    bool_values = {"true", "false", "0", "1", "yes", "no", "y", "n"}
    if all(v.lower() in bool_values for v in non_empty):
        return "boolean"

    # Check numeric
    numeric_count = 0
    for v in non_empty:
        try:
            # Clean currency or commas
            clean_v = v.replace(",", "").replace("$", "").replace("€", "").replace("£", "")
            float(clean_v)
            numeric_count += 1
        except ValueError:
            pass

    if numeric_count / len(non_empty) >= 0.85:
        return "numeric"

    # Check datetime pattern (YYYY-MM-DD or MM/DD/YYYY)
    date_pattern = re.compile(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}')
    date_count = sum(1 for v in non_empty if date_pattern.match(v))
    if date_count / len(non_empty) >= 0.85:
        return "datetime"

    return "text"

class IngestionService:
    def ingest_csv(
        self,
        file_content: bytes,
        filename: str,
        user_id: str = "default_user"
    ) -> Tuple[DatasetSchema, List[str]]:
        """Parses CSV, creates SQL table, inserts records, generates schema metadata and suggested analyses."""
        text = file_content.decode("utf-8", errors="replace")
        csv_file = io.StringIO(text)
        reader = csv.reader(csv_file)

        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("Uploaded CSV file is empty.")

        # Sanitize column names for SQL compatibility
        sanitized_columns = []
        raw_to_clean = {}
        for idx, col in enumerate(header):
            clean = re.sub(r'[^a-zA-Z0-9_]', '_', col.strip().lower())
            if not clean or clean[0].isdigit():
                clean = f"col_{clean}"
            # Handle duplicate column names
            base = clean
            counter = 1
            while clean in sanitized_columns:
                clean = f"{base}_{counter}"
                counter += 1
            sanitized_columns.append(clean)
            raw_to_clean[col] = clean

        # Read sample rows and calculate column statistics
        rows = []
        column_samples: Dict[str, List[str]] = {col: [] for col in sanitized_columns}
        for row_idx, row in enumerate(reader):
            if not row or all(not cell.strip() for cell in row):
                continue
            padded_row = row + [""] * (len(sanitized_columns) - len(row))
            row_dict = {}
            for col_name, cell_value in zip(sanitized_columns, padded_row):
                row_dict[col_name] = cell_value.strip()
                if len(column_samples[col_name]) < 50 and cell_value.strip() != "":
                    column_samples[col_name].append(cell_value.strip())
            rows.append(row_dict)

        total_rows = len(rows)
        dataset_id = f"ds_{uuid.uuid4().hex[:8]}"
        table_name = f"dataset_{dataset_id}"

        # Detect column types
        columns_info: List[ColumnInfo] = []
        numeric_cols: List[str] = []
        categorical_cols: List[str] = []
        datetime_cols: List[str] = []

        col_sql_types = {}
        for col_name in sanitized_columns:
            samples = column_samples[col_name]
            col_type = infer_column_type(samples)

            # Determine sample values and nulls
            all_vals = [r[col_name] for r in rows]
            null_count = sum(1 for v in all_vals if v == "")
            unique_count = len(set(v for v in all_vals if v != ""))

            min_val = None
            max_val = None
            if col_type == "numeric":
                numeric_cols.append(col_name)
                col_sql_types[col_name] = "REAL"
                nums = []
                for v in all_vals:
                    try:
                        clean_v = v.replace(",", "").replace("$", "")
                        if clean_v != "":
                            nums.append(float(clean_v))
                    except ValueError:
                        pass
                if nums:
                    min_val = min(nums)
                    max_val = max(nums)
            elif col_type == "datetime":
                datetime_cols.append(col_name)
                col_sql_types[col_name] = "TEXT"
            elif col_type == "boolean":
                col_sql_types[col_name] = "INTEGER"
            else:
                categorical_cols.append(col_name)
                col_sql_types[col_name] = "TEXT"

            columns_info.append(ColumnInfo(
                name=col_name,
                data_type=col_type,
                sample_values=samples[:5],
                null_count=null_count,
                unique_count=unique_count,
                min_val=min_val,
                max_val=max_val
            ))

        # Create SQL Table in Database
        conn = db_service._get_connection()
        cursor = conn.cursor()

        col_defs = ", ".join([f'"{col}" {col_sql_types[col]}' for col in sanitized_columns])
        cursor.execute(f'CREATE TABLE "{table_name}" (id INTEGER PRIMARY KEY AUTOINCREMENT, {col_defs})')

        # Insert dataset rows into table
        placeholders = ", ".join(["?"] * len(sanitized_columns))
        insert_sql = f'INSERT INTO "{table_name}" ({", ".join([f"\"{c}\"" for c in sanitized_columns])}) VALUES ({placeholders})'

        batch_tuples = []
        for r in rows:
            row_tuple = []
            for col in sanitized_columns:
                raw_val = r[col]
                if raw_val == "":
                    row_tuple.append(None)
                elif col_sql_types[col] == "REAL":
                    try:
                        clean_v = raw_val.replace(",", "").replace("$", "")
                        row_tuple.append(float(clean_v))
                    except ValueError:
                        row_tuple.append(None)
                elif col_sql_types[col] == "INTEGER" and col in [c.name for c in columns_info if c.data_type == "boolean"]:
                    row_tuple.append(1 if raw_val.lower() in ("true", "1", "yes") else 0)
                else:
                    row_tuple.append(raw_val)
            batch_tuples.append(tuple(row_tuple))

        cursor.executemany(insert_sql, batch_tuples)

        # Build schema object
        schema = DatasetSchema(
            dataset_id=dataset_id,
            filename=filename,
            table_name=table_name,
            row_count=total_rows,
            column_count=len(sanitized_columns),
            columns=columns_info,
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            datetime_columns=datetime_cols
        )

        # Store metadata in datasets table
        cursor.execute("""
            INSERT INTO datasets (dataset_id, user_id, filename, table_name, schema_json, row_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            dataset_id,
            user_id,
            filename,
            table_name,
            schema.model_dump_json(),
            total_rows
        ))

        conn.commit()
        conn.close()

        # Generate dataset-specific suggested analyses (Section 14 in Flow.md)
        suggested = self._generate_suggestions(schema)

        return schema, suggested

    def _generate_suggestions(self, schema: DatasetSchema) -> List[str]:
        suggestions = []
        num = schema.numeric_columns
        cat = schema.categorical_columns
        dt = schema.datetime_columns

        if len(num) >= 2:
            suggestions.append(f"Calculate Pearson correlation between '{num[0]}' and '{num[1]}'")
        if num and cat:
            suggestions.append(f"Aggregate average '{num[0]}' grouped by '{cat[0]}'")
        if num and dt:
            suggestions.append(f"Analyze temporal trend of '{num[0]}' over time ({dt[0]})")
        if num:
            suggestions.append(f"Calculate Coefficient of Variation (CV) for '{num[0]}'")
            suggestions.append(f"Compute summary descriptive statistics for '{num[0]}'")
        if len(cat) >= 2 and num:
            suggestions.append(f"Compare total '{num[0]}' across '{cat[1]}'")

        return suggestions[:5]

    def get_dataset(self, dataset_id: str) -> Optional[DatasetSchema]:
        conn = db_service._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT schema_json FROM datasets WHERE dataset_id = ?", (dataset_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return DatasetSchema.model_validate_json(row["schema_json"])
        return None

ingestion_service = IngestionService()

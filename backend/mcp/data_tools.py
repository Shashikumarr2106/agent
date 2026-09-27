"""Data MCP Tools exposing dataset inspection and safe SQL querying."""
from typing import Any, Dict, List, Optional
from ..services.database import db_service
from ..services.ingestion import ingestion_service

def get_dataset_schema(dataset_id: str) -> Dict[str, Any]:
    """Retrieve full column definitions, detected types, and metadata for a dataset."""
    schema = ingestion_service.get_dataset(dataset_id)
    if not schema:
        return {"error": f"Dataset '{dataset_id}' not found."}
    return schema.model_dump()

def get_dataset_metadata(dataset_id: str) -> Dict[str, Any]:
    """Retrieve high-level metadata (filename, row count, column count, column names)."""
    schema = ingestion_service.get_dataset(dataset_id)
    if not schema:
        return {"error": f"Dataset '{dataset_id}' not found."}
    return {
        "dataset_id": schema.dataset_id,
        "filename": schema.filename,
        "table_name": schema.table_name,
        "row_count": schema.row_count,
        "column_count": schema.column_count,
        "numeric_columns": schema.numeric_columns,
        "categorical_columns": schema.categorical_columns,
        "datetime_columns": schema.datetime_columns
    }

def get_sample_data(dataset_id: str, limit: int = 5) -> Dict[str, Any]:
    """Retrieve sample rows from the dataset table."""
    schema = ingestion_service.get_dataset(dataset_id)
    if not schema:
        return {"error": f"Dataset '{dataset_id}' not found."}

    sql = f'SELECT * FROM "{schema.table_name}" LIMIT {min(limit, 50)}'
    rows, err = db_service.execute_dataset_sql(sql)
    if err:
        return {"error": err}
    return {"dataset_id": dataset_id, "sample_rows": rows, "count": len(rows)}

def execute_sql(dataset_id: str, sql: str) -> Dict[str, Any]:
    """Safely execute a SELECT query against the dataset table, enforcing SELECT-only rules."""
    schema = ingestion_service.get_dataset(dataset_id)
    if not schema:
        return {"error": f"Dataset '{dataset_id}' not found."}

    rows, err = db_service.execute_dataset_sql(sql)
    if err:
        return {"error": err, "status": "failed"}
    return {
        "status": "success",
        "row_count": len(rows),
        "data": rows
    }

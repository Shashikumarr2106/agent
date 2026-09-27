"""Dataset upload and inspection API endpoints."""
import json
from typing import Any, Dict, List, Optional
from ..services.ingestion import ingestion_service
from ..services.database import db_service

def handle_upload_csv(filename: str, content_bytes: bytes, user_id: str = "default_user") -> Dict[str, Any]:
    """Ingests CSV content, creates table, stores schema, returns schema and suggestions."""
    schema, suggestions = ingestion_service.ingest_csv(content_bytes, filename, user_id=user_id)
    return {
        "dataset_id": schema.dataset_id,
        "filename": schema.filename,
        "table_name": schema.table_name,
        "row_count": schema.row_count,
        "column_count": schema.column_count,
        "columns": [c.name for c in schema.columns],
        "numeric_columns": schema.numeric_columns,
        "categorical_columns": schema.categorical_columns,
        "datetime_columns": schema.datetime_columns,
        "suggested_analyses": suggestions,
        "message": f"Successfully uploaded {filename} with {schema.row_count} rows and {schema.column_count} columns."
    }

def handle_get_dataset(dataset_id: str) -> Dict[str, Any]:
    """Retrieves dataset schema definition and sample rows."""
    schema = ingestion_service.get_dataset(dataset_id)
    if not schema:
        return {"error": f"Dataset '{dataset_id}' not found", "status": 404}

    # Fetch sample rows
    rows, _ = db_service.execute_dataset_sql(f'SELECT * FROM "{schema.table_name}" LIMIT 10')

    return {
        "dataset": schema.model_dump(),
        "sample_data": rows
    }

def handle_list_datasets(user_id: str = "default_user") -> List[Dict[str, Any]]:
    """Lists all uploaded datasets for user."""
    conn = db_service._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT dataset_id, filename, row_count, created_at FROM datasets ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

"""Dataset upload, inspection, preview, summary, and deletion API endpoints."""
from typing import Any, Dict, List, Optional
from ..services.ingestion import ingestion_service
from ..services.database import db_service

# Detect if FastAPI is available
try:
    from fastapi import APIRouter, File, UploadFile, Query, HTTPException
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = object

router = APIRouter(prefix="/datasets", tags=["Datasets"]) if HAS_FASTAPI else None

# --- Handler Functions (for both FastAPI and standalone HTTP fallback) ---

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

def handle_preview_dataset(dataset_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """Paginated preview of dataset rows."""
    return ingestion_service.get_dataset_preview(dataset_id, limit=limit, offset=offset)

def handle_summary_dataset(dataset_id: str) -> Dict[str, Any]:
    """Summary statistics for all numeric columns."""
    return ingestion_service.get_dataset_summary(dataset_id)

def handle_delete_dataset(dataset_id: str) -> Dict[str, Any]:
    """Drop dataset table and metadata."""
    return ingestion_service.delete_dataset(dataset_id)

# --- FastAPI Router Endpoints ---
if HAS_FASTAPI:
    @router.post("/upload")
    async def upload_dataset(file: UploadFile = File(...)):
        """Upload a CSV dataset, automatically detect schema types, and generate suggestions."""
        content = await file.read()
        return handle_upload_csv(file.filename, content)

    @router.get("")
    @router.get("/")
    async def list_datasets():
        """List all active uploaded datasets."""
        return handle_list_datasets()

    @router.get("/{dataset_id}")
    async def get_dataset_details(dataset_id: str):
        """Retrieve dataset schema and initial sample records."""
        res = handle_get_dataset(dataset_id)
        if res.get("error"):
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    @router.get("/{dataset_id}/preview")
    async def preview_dataset(dataset_id: str, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
        """Fetch paginated preview records from dataset SQL table."""
        res = handle_preview_dataset(dataset_id, limit, offset)
        if res.get("error"):
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    @router.get("/{dataset_id}/summary")
    async def summary_dataset(dataset_id: str):
        """Compute statistical summary (mean, std, min, max, quartiles) using Analysis SDK."""
        res = handle_summary_dataset(dataset_id)
        if res.get("error"):
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    @router.delete("/{dataset_id}")
    async def delete_dataset(dataset_id: str):
        """Delete dataset metadata and drop underlying database table."""
        res = handle_delete_dataset(dataset_id)
        if res.get("error"):
            raise HTTPException(status_code=404, detail=res["error"])
        return res

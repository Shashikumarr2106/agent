from typing import Any, Dict, List, Optional
from ..core.compat import BaseModel, Field
from datetime import datetime

class ColumnInfo(BaseModel):
    name: str
    data_type: str  # "numeric" | "text" | "datetime" | "boolean"
    sample_values: List[Any] = Field(default_factory=list)
    null_count: int = 0
    unique_count: int = 0
    min_val: Optional[Any] = None
    max_val: Optional[Any] = None

class DatasetSchema(BaseModel):
    dataset_id: str
    filename: str
    table_name: str
    row_count: int
    column_count: int
    columns: List[ColumnInfo]
    numeric_columns: List[str] = Field(default_factory=list)
    categorical_columns: List[str] = Field(default_factory=list)
    datetime_columns: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

class DatasetUploadResponse(BaseModel):
    dataset_id: str
    filename: str
    table_name: str
    row_count: int
    columns: List[str]
    suggested_analyses: List[str] = Field(default_factory=list)
    message: str

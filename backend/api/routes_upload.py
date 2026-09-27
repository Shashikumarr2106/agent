"""Backward-compatible proxy re-exporting dataset handlers from routes_datasets."""
from .routes_datasets import (
    router,
    handle_upload_csv,
    handle_get_dataset,
    handle_list_datasets,
    handle_preview_dataset,
    handle_summary_dataset,
    handle_delete_dataset
)

__all__ = [
    "router",
    "handle_upload_csv",
    "handle_get_dataset",
    "handle_list_datasets",
    "handle_preview_dataset",
    "handle_summary_dataset",
    "handle_delete_dataset"
]

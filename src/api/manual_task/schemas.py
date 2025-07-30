from typing import Union
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional
from datetime import datetime

# -------------------------------
# Request models
# -------------------------------

class AttributeData(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None

class ExtraData(BaseModel):
    name: str
    value: str

class DocumentData(BaseModel):
    url: str
    type: Optional[str] = "document"
    description: Optional[str] = ""

class SellerData(BaseModel):
    name: str
    type: Optional[str] = "distributor"

class ManualImputationRequest(BaseModel):
    part_number: str = Field(..., description="Part number to update")
    editor: str = Field(..., description="Username of the editor")
    notes: Optional[str] = Field(None, description="Notes about the changes")
    source_url: Optional[str] = Field(None, description="Source URL for traceability")
    batch_id: Optional[str] = Field(None, description="Batch identifier for grouping")
    attributes: Optional[List[AttributeData]] = Field(None, description="Product attributes to add/update")
    extras: Optional[List[ExtraData]] = Field(None, description="Product extras to add/update")
    documents: Optional[List[DocumentData]] = Field(None, description="Documents/media to add")
    sellers: Optional[List[SellerData]] = Field(None, description="Sellers to add")

class ValidationRequest(BaseModel):
    validator: str = Field(..., description="Username of the validator")
    validation_notes: Optional[str] = Field(None, description="Validation notes")

class ManualTaskUpdateRequest(BaseModel):
    note: Optional[str]
    source_url: Optional[str]

# New simplified schemas
# Enhanced data models with individual notes and source (define first)
class AttributeDataWithMeta(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None
    notes: Optional[str] = Field(None, description="Individual notes for this attribute")
    source_url: Optional[str] = Field(None, description="Individual source URL for this attribute")

class ExtraDataWithMeta(BaseModel):
    name: str
    value: str
    notes: Optional[str] = Field(None, description="Individual notes for this extra")
    source_url: Optional[str] = Field(None, description="Individual source URL for this extra")

class DocumentDataWithMeta(BaseModel):
    url: str
    type: Optional[str] = "document"
    description: Optional[str] = ""
    notes: Optional[str] = Field(None, description="Individual notes for this document")
    source_url: Optional[str] = Field(None, description="Individual source URL for this document")

class SellerDataWithMeta(BaseModel):
    name: str
    type: Optional[str] = "distributor"
    notes: Optional[str] = Field(None, description="Individual notes for this seller")
    source_url: Optional[str] = Field(None, description="Individual source URL for this seller")

class SimpleTaskRequest(BaseModel):
    product_id: Optional[int] = Field(None, description="Product ID (use this OR part_number)")
    part_number: Optional[str] = Field(None, description="Part number (use this OR product_id)")
    editor: str = Field(..., description="Username of the editor")
    notes: Optional[str] = Field(None, description="Notes about the task")

class ProcessTaskRequest(BaseModel):
    task_id: int = Field(..., description="Task ID to process")
    category_id: Optional[str] = Field(None, description="Category ID to assign to product")
    attributes: Optional[List[AttributeDataWithMeta]] = Field(None, description="Product attributes to add/update")
    extras: Optional[List[ExtraDataWithMeta]] = Field(None, description="Product extras to add/update")
    documents: Optional[List[DocumentDataWithMeta]] = Field(None, description="Documents/media to add")
    sellers: Optional[List[SellerDataWithMeta]] = Field(None, description="Sellers to add")

# -------------------------------
# Response models
# -------------------------------

class ManualImputationResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[int] = None
    part_number: Optional[str] = None
    affected_tables: Optional[List[str]] = None
    changes_count: Optional[int] = None

class TaskHistoryResponse(BaseModel):
    id: int
    product_id: Optional[int]
    editor: str
    current_status: str
    task_type: str
    note: Optional[str]
    source_url: Optional[str]
    batch_id: Optional[str]
    validated: bool
    validator: Optional[str]
    validation_date: Optional[datetime]
    processing_info: Optional[Dict]
    error_message: Optional[str]
    edited_fields: Optional[Dict]
    affected_tables: Optional[List[str]]
    changes_summary: Optional[Dict]
    created_date: datetime
    updated_date: datetime


# -------------------------------
# Batch Operations Schemas
# -------------------------------

class BatchTaskRequest(BaseModel):
    tasks: List[ManualImputationRequest] = Field(..., description="List of tasks to create")
    batch_id: Optional[str] = Field(None, description="Optional batch identifier")

class BatchTaskResult(BaseModel):
    index: int
    task_id: Optional[int] = None
    part_number: str
    status: str  # 'success' or 'failed'
    error: Optional[str] = None

class BatchTaskResponse(BaseModel):
    status: str
    batch_id: str
    summary: Dict[str, int]
    results: List[BatchTaskResult]

# -------------------------------
# CSV Import Schema
# -------------------------------

class CSVImportRequest(BaseModel):
    editor: str = Field(..., description="Editor performing the import")
    batch_id: Optional[str] = Field(None, description="Optional batch identifier")
    validate_only: bool = Field(False, description="Only validate, don't create tasks")

class CSVImportResponse(BaseModel):
    status: str
    batch_id: Optional[str] = None
    total_rows: int
    successful: int
    failed: int
    validation_errors: List[Dict[str, str]] = []
    created_tasks: List[int] = []


# -------------------------------
# Advanced Search Schema
# -------------------------------
class AdvancedSearchRequest(BaseModel):
    query: Optional[str] = None
    manufacturer_id: Optional[int] = None
    category_id: Optional[str] = None
    editor: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    has_attributes: Optional[bool] = None
    has_documents: Optional[bool] = None
    sort_by: str = "relevance"
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100)

class SearchResult(BaseModel):
    part_number: str
    product_id: Optional[int]
    manufacturer: Optional[str]
    category: Optional[str]
    last_updated: Optional[datetime]
    attributes_count: int = 0
    documents_count: int = 0

class AdvancedSearchResponse(BaseModel):
    results: List[SearchResult]
    pagination: Dict[str, int]
    filters_applied: Dict[str, Union[str, int, bool]]
    total_found: int
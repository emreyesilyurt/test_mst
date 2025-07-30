from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from typing import List, Optional
import io
from datetime import datetime
from src.services.manual_imputation_service import ManualImputationService
from .schemas import (
    ManualImputationRequest,
    ManualImputationResponse,
    TaskHistoryResponse,
    ValidationRequest,
    ManualTaskUpdateRequest,
    SimpleTaskRequest,
    ProcessTaskRequest,
    BatchTaskRequest,
    BatchTaskResponse,
    CSVImportRequest,
    CSVImportResponse,
    AdvancedSearchRequest,
    AdvancedSearchResponse
)


router = APIRouter()

async def get_manual_imputation_service():
    return ManualImputationService()

@router.post("/imputation/", response_model=ManualImputationResponse)
async def create_manual_imputation(
    request: ManualImputationRequest,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    try:
        data_updates = {}
        if request.attributes:
            data_updates['attributes'] = [attr.dict() for attr in request.attributes]
        if request.extras:
            data_updates['extras'] = [extra.dict() for extra in request.extras]
        if request.documents:
            data_updates['documents'] = [doc.dict() for doc in request.documents]
        if request.sellers:
            data_updates['sellers'] = [seller.dict() for seller in request.sellers]
        if not data_updates:
            raise HTTPException(status_code=400, detail="No data updates provided. Please include at least one of: attributes, extras, documents, or sellers.")
        result = await service.create_manual_task(
            part_number=request.part_number,
            editor=request.editor,
            data_updates=data_updates,
            notes=request.notes,
            source_url=request.source_url,
            batch_id=request.batch_id
        )
        return ManualImputationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/history/", response_model=List[TaskHistoryResponse])
async def get_manual_task_history(
    part_number: Optional[str] = Query(None, description="Filter by part number"),
    editor: Optional[str] = Query(None, description="Filter by editor"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    try:
        tasks = await service.get_manual_task_history(part_number=part_number, editor=editor, limit=limit)
        return [TaskHistoryResponse(**task) for task in tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/validate/{task_id}/")
async def validate_manual_task(
    task_id: int,
    request: ValidationRequest,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    try:
        result = await service.validate_manual_task(
            task_id=task_id,
            validator=request.validator,
            validation_notes=request.validation_notes
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/task/{task_id}/")
async def get_manual_task_details(
    task_id: int,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    try:
        task = await service.get_manual_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Manual task {task_id} not found")
        return task
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/task/{task_id}/")
async def update_manual_task_metadata(
    task_id: int,
    request: ManualTaskUpdateRequest,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    try:
        updated = await service.update_task_metadata(task_id, request.note, request.source_url)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found or not updated")
        return {"message": "Manual task metadata updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/task/{task_id}/")
async def delete_manual_task(
    task_id: int,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    try:
        deleted = await service.delete_task(task_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found or already deleted")
        return {"message": f"Task {task_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# New endpoints for enhanced functionality

# @router.get("/tasks/")
# async def get_tasks_by_filters(
#     product_id: Optional[int] = Query(None, description="Filter by product ID"),
#     part_number: Optional[str] = Query(None, description="Filter by part number"),
#     last_updated_days: Optional[int] = Query(None, description="Filter by tasks updated in last N days"),
#     status: Optional[str] = Query(None, description="Filter by task status"),
#     editor: Optional[str] = Query(None, description="Filter by editor"),
#     limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
#     service: ManualImputationService = Depends(get_manual_imputation_service)
# ):
#     """Get tasks with various filtering options"""
#     try:
#         tasks = await service.get_tasks_by_filters(
#             product_id=product_id,
#             part_number=part_number,
#             last_updated_days=last_updated_days,
#             status=status,
#             editor=editor,
#             limit=limit
#         )
#         return tasks
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
@router.get("/tasks/")
async def get_tasks_by_filters(
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    part_number: Optional[str] = Query(None, description="Filter by part number"),
    last_updated_days: Optional[int] = Query(None, description="Filter by tasks updated in last N days"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    editor: Optional[str] = Query(None, description="Filter by editor"),
    batch_id: Optional[str] = Query(None, description="Filter by batch ID"),  # Add this line
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """Get tasks with various filtering options"""
    try:
        tasks = await service.get_tasks_by_filters(
            product_id=product_id,
            part_number=part_number,
            last_updated_days=last_updated_days,
            status=status,
            editor=editor,
            batch_id=batch_id,  # Add this line
            limit=limit
        )
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/partnumbers/search/")
async def search_part_numbers(
    query: str = Query(..., description="Search query for part numbers"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results to return"),
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """Search part numbers and get related product information"""
    try:
        results = await service.search_part_numbers(query=query, limit=limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/product/{product_id}/details/")
async def get_product_details(
    product_id: int,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """Get complete product details including attributes, extras, category, etc."""
    try:
        product_details = await service.get_product_details(product_id=product_id)
        if not product_details:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        return product_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/partnumber/{part_number}/product/")
async def get_product_by_part_number(
    part_number: str,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """Get product details by part number"""
    try:
        product_details = await service.get_product_by_part_number(part_number=part_number)
        if not product_details:
            raise HTTPException(status_code=404, detail=f"Product with part number {part_number} not found")
        return product_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# New simplified workflow endpoints

@router.post("/task/create/")
async def create_simple_task(
    request: SimpleTaskRequest,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """Create a simple manual task with just product identification and basic info"""
    try:
        if not request.product_id and not request.part_number:
            raise HTTPException(status_code=400, detail="Either product_id or part_number must be provided")
        
        if request.product_id and request.part_number:
            raise HTTPException(status_code=400, detail="Provide either product_id OR part_number, not both")
        
        result = await service.create_simple_task(
            product_id=request.product_id,
            part_number=request.part_number,
            editor=request.editor,
            notes=request.notes
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/task/process/")
async def process_task_data(
    request: ProcessTaskRequest,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """Process a task with detailed data including individual notes and sources"""
    try:
        result = await service.process_task_data(
            task_id=request.task_id,
            category_id=request.category_id,
            attributes=request.attributes,
            extras=request.extras,
            documents=request.documents,
            sellers=request.sellers
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Category and Attribute management endpoints

@router.get("/categories/")
async def get_categories(
    parent_id: Optional[str] = Query(None, description="Parent category ID to get children"),
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """Get categories, optionally filtered by parent"""
    try:
        categories = await service.get_categories(parent_id=parent_id)
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/categories/")
async def create_category(
    name: str,
    parent_id: Optional[str] = None,
    product_category: bool = False,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """Create a new category"""
    try:
        category = await service.create_category(
            name=name,
            parent_id=parent_id,
            product_category=product_category
        )
        return category
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/attributes/")
async def get_attributes(
    category_id: Optional[str] = Query(None, description="Category ID to get related attributes"),
    search: Optional[str] = Query(None, description="Search attributes by name"),
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """Get attributes, optionally filtered by category or search term"""
    try:
        attributes = await service.get_attributes(category_id=category_id, search=search)
        return attributes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/attributes/")
async def create_attribute(
    name: str,
    desc: Optional[str] = None,
    category_id: Optional[str] = None,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """Create a new attribute and optionally link it to a category"""
    try:
        attribute = await service.create_attribute(
            name=name,
            desc=desc,
            category_id=category_id
        )
        return attribute
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/products/")
async def get_products(
    search: Optional[str] = Query(None, description="Search products by part number"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of products to return"),
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """Get products with part numbers for dropdown selection"""
    try:
        products = await service.get_products_for_selection(search=search, limit=limit)
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ================================
# BATCH OPERATIONS ENDPOINTS
# ================================

@router.post("/batch/create/", response_model=BatchTaskResponse)
async def create_batch_tasks(
    request: BatchTaskRequest,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """
    Create multiple manual tasks in a single batch operation.
    
    This endpoint allows you to create multiple manual imputation tasks at once,
    which is useful for bulk data entry operations.
    """
    try:
        # Convert Pydantic models to dictionaries for processing
        tasks_data = []
        for task in request.tasks:
            task_dict = task.dict()
            
            # Prepare data_updates dictionary
            data_updates = {}
            if task_dict.get('attributes'):
                data_updates['attributes'] = task_dict['attributes']
            if task_dict.get('extras'):
                data_updates['extras'] = task_dict['extras']
            if task_dict.get('documents'):
                data_updates['documents'] = task_dict['documents']
            if task_dict.get('sellers'):
                data_updates['sellers'] = task_dict['sellers']
            
            task_dict['data_updates'] = data_updates
            tasks_data.append(task_dict)
        
        # Process batch
        results = await service.create_batch_tasks(tasks_data, request.batch_id)
        
        return BatchTaskResponse(
            status="success" if len(results["failed"]) == 0 else "partial_success",
            batch_id=results["batch_id"],
            summary={
                "total": results["total_count"],
                "successful": len(results["successful"]),
                "failed": len(results["failed"])
            },
            results=results["successful"] + results["failed"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch operation failed: {str(e)}")


@router.post("/batch/import-csv/", response_model=CSVImportResponse)
async def import_batch_from_csv(
    file: UploadFile = File(..., description="CSV file to import"),
    editor: str = Query(..., description="Editor performing the import"),
    batch_id: Optional[str] = Query(None, description="Optional batch identifier"),
    validate_only: bool = Query(False, description="Only validate without creating tasks"),
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """
    Import multiple manual tasks from a CSV file.
    
    Expected CSV columns:
    - part_number (required): The part number to create a task for
    - notes (optional): Notes about the task
    - source_url (optional): Source URL for traceability
    - attribute_name (optional): Name of attribute to add
    - attribute_value (optional): Value of attribute (required if attribute_name provided)
    - attribute_unit (optional): Unit for the attribute
    - extra_name (optional): Name of extra field to add
    - extra_value (optional): Value of extra field (required if extra_name provided)
    - document_url (optional): URL of document to add
    - document_type (optional): Type of document (default: 'document')
    - document_description (optional): Description of document
    - seller_name (optional): Name of seller to add
    - seller_type (optional): Type of seller (default: 'distributor')
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    try:
        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Process CSV import
        results = await service.process_csv_import(
            csv_content=csv_content,
            editor=editor,
            batch_id=batch_id,
            validate_only=validate_only
        )
        
        return CSVImportResponse(
            status=results["status"],
            batch_id=results.get("batch_id"),
            total_rows=results["total_rows"],
            successful=results["successful"],
            failed=results["failed"],
            validation_errors=results["validation_errors"],
            created_tasks=results.get("created_tasks", [])
        )
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be encoded in UTF-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV import failed: {str(e)}")


@router.get("/search/advanced/", response_model=AdvancedSearchResponse)
async def advanced_search(
    query: Optional[str] = Query(None, description="Search term for part numbers"),
    manufacturer_id: Optional[int] = Query(None, description="Filter by manufacturer ID"),
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    editor: Optional[str] = Query(None, description="Filter by editor who last modified"),
    date_from: Optional[datetime] = Query(None, description="Filter by date range start"),
    date_to: Optional[datetime] = Query(None, description="Filter by date range end"),
    has_attributes: Optional[bool] = Query(None, description="Filter products with/without attributes"),
    has_documents: Optional[bool] = Query(None, description="Filter products with/without documents"),
    sort_by: str = Query("relevance", description="Sort by: relevance, name, date_desc, date_asc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """
    Perform advanced search with multiple filters and sorting options.
    
    This endpoint provides comprehensive search functionality with:
    - Text search across part numbers
    - Multiple filter criteria
    - Sorting options
    - Pagination support
    """
    try:
        # Build filters dictionary
        filters = {}
        if manufacturer_id is not None:
            filters['manufacturer_id'] = manufacturer_id
        if category_id is not None:
            filters['category_id'] = category_id
        if editor is not None:
            filters['editor'] = editor
        if date_from is not None and date_to is not None:
            filters['date_range'] = (date_from, date_to)
        if has_attributes is not None:
            filters['has_attributes'] = has_attributes
        if has_documents is not None:
            filters['has_documents'] = has_documents
        
        # Perform search
        results = await service.advanced_search(
            query=query,
            filters=filters,
            sort_by=sort_by,
            page=page,
            page_size=page_size
        )
        
        return AdvancedSearchResponse(
            results=results["results"],
            pagination=results["pagination"],
            filters_applied=results["filters_applied"],
            total_found=results["total_found"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Advanced search failed: {str(e)}")


@router.get("/batch/{batch_id}/status/")
async def get_batch_status(
    batch_id: str,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """
    Get the status of a batch operation.
    
    This endpoint allows you to check the progress and results of a batch operation
    using the batch ID returned from batch creation or CSV import.
    """
    try:
        # Get tasks by batch_id
        tasks = await service.get_tasks_by_filters(
            batch_id=batch_id,
            limit=1000  # High limit to get all tasks in batch
        )
        
        # Calculate status summary
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.get('current_status') == 'completed'])
        failed_tasks = len([t for t in tasks if t.get('current_status') == 'failed'])
        processing_tasks = total_tasks - completed_tasks - failed_tasks
        
        return {
            "batch_id": batch_id,
            "total_tasks": total_tasks,
            "completed": completed_tasks,
            "failed": failed_tasks,
            "processing": processing_tasks,
            "completion_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "tasks": tasks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get batch status: {str(e)}")


@router.delete("/batch/{batch_id}/")
async def cancel_batch_operation(
    batch_id: str,
    service: ManualImputationService = Depends(get_manual_imputation_service)
):
    """
    Cancel a batch operation (delete all tasks in the batch).
    
    WARNING: This will permanently delete all tasks associated with the batch ID.
    Only use this for cancelling operations that are still in progress or
    for cleaning up failed batch operations.
    """
    try:
        # Get all tasks in the batch
        tasks = await service.get_tasks_by_filters(
            batch_id=batch_id,
            limit=1000
        )
        
        if not tasks:
            raise HTTPException(status_code=404, detail=f"No tasks found for batch {batch_id}")
        
        # Delete each task in the batch
        deleted_count = 0
        failed_deletions = []
        
        for task in tasks:
            try:
                success = await service.delete_task(task['id'])
                if success:
                    deleted_count += 1
                else:
                    failed_deletions.append(task['id'])
            except Exception as e:
                failed_deletions.append(task['id'])
        
        return {
            "batch_id": batch_id,
            "total_tasks": len(tasks),
            "deleted": deleted_count,
            "failed_deletions": failed_deletions,
            "status": "completed" if len(failed_deletions) == 0 else "partial"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel batch: {str(e)}")
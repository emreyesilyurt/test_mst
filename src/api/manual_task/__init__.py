from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from src.services.manual_imputation_service import ManualImputationService
from .schemas import (
    ManualImputationRequest,
    ManualImputationResponse,
    TaskHistoryResponse,
    ValidationRequest,
    ManualTaskUpdateRequest,
    SimpleTaskRequest,
    ProcessTaskRequest
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

@router.get("/tasks/")
async def get_tasks_by_filters(
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    part_number: Optional[str] = Query(None, description="Filter by part number"),
    last_updated_days: Optional[int] = Query(None, description="Filter by tasks updated in last N days"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    editor: Optional[str] = Query(None, description="Filter by editor"),
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

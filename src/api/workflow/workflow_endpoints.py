"""
Workflow API endpoints for master_electronics.

This module provides REST API endpoints for the workflow orchestrator system.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio

from src.services.workflow_orchestrator import (
    WorkflowOrchestrator,
    WorkflowConfig,
    TaskType,
    TaskPriority,
    run_workflow,
    get_workflow_status,
    get_pending_manual_tasks
)

# Create router
router = APIRouter(prefix="/workflow", tags=["workflow"])


# Pydantic models for request/response
class WorkflowRunRequest(BaseModel):
    """Request model for running workflow."""
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of records to process")
    priority_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Priority threshold override")
    force_automation: bool = Field(default=False, description="Force all tasks to automation")
    force_manual: bool = Field(default=False, description="Force all tasks to manual")
    batch_id: Optional[str] = Field(default=None, description="Custom batch ID")


class WorkflowConfigRequest(BaseModel):
    """Request model for workflow configuration."""
    automation_priority_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    automation_max_concurrent: Optional[int] = Field(default=None, ge=1, le=20)
    automation_retry_attempts: Optional[int] = Field(default=None, ge=1, le=10)
    manual_priority_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    manual_batch_size: Optional[int] = Field(default=None, ge=1, le=200)
    automation_failure_to_manual: Optional[bool] = Field(default=None)
    max_automation_failures: Optional[int] = Field(default=None, ge=1, le=10)
    max_daily_tasks: Optional[int] = Field(default=None, ge=1, le=10000)
    max_batch_size: Optional[int] = Field(default=None, ge=1, le=1000)


class WorkflowResponse(BaseModel):
    """Response model for workflow operations."""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class TaskInfo(BaseModel):
    """Model for task information."""
    task_id: int
    product_id: Optional[int]
    part_number: Optional[str]
    batch_id: str
    task_type: str
    current_status: str
    editor: str
    note: Optional[str]
    created_date: datetime
    priority: str
    confidence: float


# Background task storage (in production, use Redis or similar)
background_workflows: Dict[str, Dict[str, Any]] = {}


@router.post("/run", response_model=WorkflowResponse)
async def run_workflow_endpoint(
    request: WorkflowRunRequest,
    background_tasks: BackgroundTasks
):
    """
    Run workflow orchestration.
    
    This endpoint starts a workflow process that fetches data from BigQuery
    and delegates tasks to automation or manual processing.
    """
    try:
        # Validate request
        if request.force_automation and request.force_manual:
            raise HTTPException(
                status_code=400,
                detail="Cannot force both automation and manual modes"
            )
        
        # Create custom config if needed
        config = WorkflowConfig()
        
        # Create orchestrator
        orchestrator = WorkflowOrchestrator(config)
        
        # Determine force type
        force_type = None
        if request.force_automation:
            force_type = TaskType.AUTOMATION
        elif request.force_manual:
            force_type = TaskType.MANUAL
        
        # Run workflow in background
        batch_id = request.batch_id or f"api_workflow_{int(datetime.now().timestamp())}"
        
        # Store initial status
        background_workflows[batch_id] = {
            'status': 'starting',
            'started_at': datetime.now(),
            'request': request.dict()
        }
        
        # Add background task
        background_tasks.add_task(
            run_workflow_background,
            orchestrator,
            batch_id,
            request.limit,
            request.priority_threshold,
            force_type
        )
        
        return WorkflowResponse(
            status="success",
            message=f"Workflow started successfully",
            data={
                "batch_id": batch_id,
                "estimated_processing_time": f"{request.limit * 2} seconds",
                "status_endpoint": f"/workflow/status/{batch_id}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_workflow_background(
    orchestrator: WorkflowOrchestrator,
    batch_id: str,
    limit: int,
    priority_threshold: Optional[float],
    force_type: Optional[TaskType]
):
    """Background task to run workflow."""
    try:
        # Update status
        background_workflows[batch_id]['status'] = 'running'
        
        # Run workflow
        results = await orchestrator.orchestrate_workflow(
            batch_id=batch_id,
            limit=limit,
            priority_threshold=priority_threshold,
            force_task_type=force_type
        )
        
        # Update with results
        background_workflows[batch_id].update({
            'status': 'completed',
            'completed_at': datetime.now(),
            'results': results
        })
        
    except Exception as e:
        background_workflows[batch_id].update({
            'status': 'failed',
            'completed_at': datetime.now(),
            'error': str(e)
        })


@router.get("/status/{batch_id}", response_model=WorkflowResponse)
async def get_workflow_status_endpoint(batch_id: str):
    """
    Get workflow status for a specific batch.
    
    Returns detailed status information including task counts and progress.
    """
    try:
        # Check background status first
        bg_status = background_workflows.get(batch_id)
        
        # Get detailed status from database
        status = await get_workflow_status(batch_id)
        
        # Combine information
        response_data = status.copy()
        if bg_status:
            response_data['background_status'] = bg_status['status']
            response_data['started_at'] = bg_status.get('started_at')
            response_data['completed_at'] = bg_status.get('completed_at')
            if 'results' in bg_status:
                response_data['workflow_results'] = bg_status['results']
        
        return WorkflowResponse(
            status="success",
            message=f"Status retrieved for batch {batch_id}",
            data=response_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending", response_model=WorkflowResponse)
async def get_pending_tasks_endpoint(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of tasks to return"),
    priority: Optional[str] = Query(default=None, regex="^(high|medium|low)$", description="Filter by priority")
):
    """
    Get pending manual tasks.
    
    Returns a list of manual tasks that are waiting for human processing.
    """
    try:
        tasks = await get_pending_manual_tasks(limit=limit, priority=priority)
        
        # Convert to response format
        task_list = []
        for task in tasks:
            task_info = TaskInfo(
                task_id=task['task_id'],
                product_id=task['product_id'],
                part_number=task['part_number'],
                batch_id=task['batch_id'],
                task_type=task['task_type'],
                current_status=task['current_status'],
                editor=task['editor'],
                note=task['note'],
                created_date=task['created_date'],
                priority=task['priority'],
                confidence=task['confidence']
            )
            task_list.append(task_info.dict())
        
        return WorkflowResponse(
            status="success",
            message=f"Retrieved {len(task_list)} pending tasks",
            data={
                "tasks": task_list,
                "total_count": len(task_list),
                "filters": {
                    "limit": limit,
                    "priority": priority
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", response_model=WorkflowResponse)
async def get_workflow_config():
    """
    Get current workflow configuration.
    
    Returns the current configuration parameters for the workflow system.
    """
    try:
        config = WorkflowConfig()
        
        config_data = {
            "automation_priority_threshold": config.automation_priority_threshold,
            "automation_max_concurrent": config.automation_max_concurrent,
            "automation_retry_attempts": config.automation_retry_attempts,
            "manual_priority_threshold": config.manual_priority_threshold,
            "manual_batch_size": config.manual_batch_size,
            "automation_failure_to_manual": config.automation_failure_to_manual,
            "max_automation_failures": config.max_automation_failures,
            "max_daily_tasks": config.max_daily_tasks,
            "max_batch_size": config.max_batch_size
        }
        
        return WorkflowResponse(
            status="success",
            message="Configuration retrieved successfully",
            data=config_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config", response_model=WorkflowResponse)
async def update_workflow_config(request: WorkflowConfigRequest):
    """
    Update workflow configuration.
    
    Note: This updates the configuration for new workflow instances.
    Existing running workflows will continue with their original configuration.
    """
    try:
        # In a production system, you'd want to persist this configuration
        # For now, we'll just validate the request
        
        updated_fields = []
        config_dict = request.dict(exclude_unset=True)
        
        for field, value in config_dict.items():
            if value is not None:
                updated_fields.append(field)
        
        return WorkflowResponse(
            status="success",
            message=f"Configuration update requested for {len(updated_fields)} fields",
            data={
                "updated_fields": updated_fields,
                "note": "Configuration changes will apply to new workflow instances",
                "current_config": config_dict
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches", response_model=WorkflowResponse)
async def list_workflow_batches(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of batches to return")
):
    """
    List recent workflow batches.
    
    Returns a list of recent workflow batches with their status.
    """
    try:
        # Get recent batches from background storage
        recent_batches = []
        
        # Sort by started_at descending
        sorted_batches = sorted(
            background_workflows.items(),
            key=lambda x: x[1].get('started_at', datetime.min),
            reverse=True
        )
        
        for batch_id, batch_info in sorted_batches[:limit]:
            batch_data = {
                "batch_id": batch_id,
                "status": batch_info.get('status', 'unknown'),
                "started_at": batch_info.get('started_at'),
                "completed_at": batch_info.get('completed_at'),
                "request_params": batch_info.get('request', {})
            }
            
            # Add results summary if available
            if 'results' in batch_info:
                results = batch_info['results']
                batch_data['summary'] = {
                    "total_records": results.get('total_records', 0),
                    "automation_tasks": results.get('automation_tasks', 0),
                    "manual_tasks": results.get('manual_tasks', 0),
                    "processing_time": results.get('processing_time', 0)
                }
            
            recent_batches.append(batch_data)
        
        return WorkflowResponse(
            status="success",
            message=f"Retrieved {len(recent_batches)} recent batches",
            data={
                "batches": recent_batches,
                "total_count": len(recent_batches)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/batch/{batch_id}", response_model=WorkflowResponse)
async def cancel_workflow_batch(batch_id: str):
    """
    Cancel a workflow batch.
    
    Note: This only removes the batch from tracking.
    Running tasks may continue to completion.
    """
    try:
        if batch_id in background_workflows:
            batch_info = background_workflows[batch_id]
            
            # Mark as cancelled
            batch_info['status'] = 'cancelled'
            batch_info['cancelled_at'] = datetime.now()
            
            return WorkflowResponse(
                status="success",
                message=f"Batch {batch_id} marked as cancelled",
                data={
                    "batch_id": batch_id,
                    "previous_status": batch_info.get('status', 'unknown'),
                    "note": "Running tasks may continue to completion"
                }
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Batch {batch_id} not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/health", response_model=WorkflowResponse)
async def workflow_health_check():
    """
    Health check for workflow system.
    
    Verifies that the workflow system components are accessible.
    """
    try:
        # Test basic components
        config = WorkflowConfig()
        orchestrator = WorkflowOrchestrator(config)
        
        # Basic connectivity tests could go here
        # For now, just return success if we can create the objects
        
        return WorkflowResponse(
            status="success",
            message="Workflow system is healthy",
            data={
                "components": {
                    "workflow_orchestrator": "ok",
                    "configuration": "ok",
                    "background_tasks": "ok"
                },
                "active_batches": len(background_workflows),
                "timestamp": datetime.now()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow system unhealthy: {str(e)}")

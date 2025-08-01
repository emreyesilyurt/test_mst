from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.manual_task import router as manual_task_router
from src.api.workflow import router as workflow_router

app = FastAPI(
    title="Master Electronics API",
    description="API for manual data imputation tasks and workflow orchestration in electronics database",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(manual_task_router, prefix="/manual", tags=["Manual Imputation"])
app.include_router(workflow_router, tags=["Workflow Orchestration"])

@app.get("/")
async def root():
    return {
        "message": "Master Electronics API is running",
        "docs": "/docs",
        "endpoints": {
            "manual_tasks": "/manual",
            "workflow": "/workflow",
            "health": "/workflow/health"
        },
        "features": [
            "Manual data imputation tasks",
            "Workflow orchestration",
            "BigQuery integration",
            "Automation task management",
            "Task delegation system"
        ]
    }

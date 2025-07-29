from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.manual_task import router as manual_task_router

app = FastAPI(
    title="Manual Task API",
    description="API for manual data imputation tasks in electronics database",
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

@app.get("/")
async def root():
    return {
        "message": "Manual Task API is running",
        "docs": "/docs",
        "manual_endpoints": "/manual"
    }

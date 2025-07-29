#!/usr/bin/env python3
"""
FastAPI server startup script for the Manual Task API.
"""

import uvicorn
import os

if __name__ == "__main__":
    print("Starting Manual Task API server...")
    print("API will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    print("Manual Task Interface at: file:///" + os.path.abspath("src/ui/manual_task_interface.html"))
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

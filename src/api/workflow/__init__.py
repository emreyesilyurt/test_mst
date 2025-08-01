"""
Workflow API module for master_electronics.

This module provides REST API endpoints for the workflow orchestrator system.
"""

from .workflow_endpoints import router

__all__ = ['router']

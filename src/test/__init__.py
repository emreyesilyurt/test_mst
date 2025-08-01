"""
Test package for Workflow Orchestrator System

This package contains comprehensive tests for the workflow orchestration system,
including smoke tests, integration tests, and utilities for testing the
master_electronics workflow system.

Test Modules:
- test_workflow_smoke: Basic functionality tests without external dependencies
- test_workflow_integration: End-to-end tests with real data processing

Usage:
    # Run individual test modules
    python src/test/test_workflow_smoke.py
    python src/test/test_workflow_integration.py
    
    # Or use the main test runner
    python run_tests.py all
"""

__version__ = "1.0.0"
__author__ = "Master Electronics Team"

# Test configuration constants
TEST_CONFIG = {
    'default_test_limit': 5,
    'max_test_records': 20,
    'test_timeout': 60,
    'test_batch_prefix': 'test_',
    'smoke_test_prefix': 'smoke_test_',
    'integration_test_prefix': 'integration_test_'
}

# Test result file names
TEST_RESULT_FILES = {
    'smoke': 'smoke_test_results.json',
    'integration': 'integration_test_results.json'
}

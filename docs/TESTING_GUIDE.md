# Testing Guide for Workflow Orchestrator

This guide explains how to test the workflow orchestrator system to ensure it's working correctly in your environment.

## Overview

The testing suite includes multiple types of tests to verify different aspects of the workflow system:

1. **Smoke Tests** - Basic functionality without external dependencies
2. **Integration Tests** - End-to-end testing with real data processing
3. **CLI Tests** - Command-line interface functionality
4. **API Tests** - REST API endpoint verification
5. **Quick Tests** - Fast workflow functionality check

## Test Files

- `run_tests.py` - Main test runner (recommended)
- `src/test/test_workflow_smoke.py` - Comprehensive smoke tests
- `src/test/test_workflow_integration.py` - Integration tests with real data
- `run_workflow.py` - CLI tool (also used for testing)

## Quick Start

### 1. Run All Tests
```bash
python run_tests.py all
```

### 2. Run Individual Test Types
```bash
# Basic functionality tests (recommended first)
python run_tests.py smoke

# End-to-end tests with real data
python run_tests.py integration

# CLI interface tests
python run_tests.py cli

# API endpoint tests
python run_tests.py api

# Quick workflow test
python run_tests.py quick
```

## Detailed Test Descriptions

### Smoke Tests (`python run_tests.py smoke`)

**Purpose**: Verify basic system functionality without external dependencies.

**What it tests**:
- ✅ Module imports and dependencies
- ✅ Configuration object creation
- ✅ WorkflowOrchestrator initialization
- ✅ Database connectivity
- ✅ Decision engine logic with mock data
- ✅ Data completeness calculation
- ✅ Error handling with invalid data
- ✅ API endpoint configuration
- ✅ CLI interface availability

**Expected results**: All tests should pass even without BigQuery or DigiKey API configured.

**Run directly**:
```bash
python test_workflow_smoke.py
```

### Integration Tests (`python run_tests.py integration`)

**Purpose**: Test end-to-end workflow functionality with real data processing.

**What it tests**:
- 🔄 Small manual workflow execution
- 🤖 Small automation workflow execution
- 🎯 Mixed workflow with natural decision making
- 📊 Workflow status monitoring
- 📋 Pending manual tasks retrieval
- ⚙️ Configuration variations
- 🛡️ Error recovery mechanisms
- ⚡ Performance baseline establishment

**Expected results**: 
- Tests will show warnings if BigQuery is not configured (this is normal)
- Automation tests may fail if DigiKey API is not configured (this is expected)
- Manual task creation should work regardless

**Run directly**:
```bash
python test_workflow_integration.py
```

### CLI Tests (`python run_tests.py cli`)

**Purpose**: Verify command-line interface functionality.

**What it tests**:
- 💻 Help commands for all CLI functions
- 📋 Configuration display
- 🔧 Command parsing and validation

**Expected results**: All CLI commands should respond correctly.

### API Tests (`python run_tests.py api`)

**Purpose**: Verify REST API endpoint configuration.

**What it tests**:
- 🌐 API module imports
- 📡 Endpoint route configuration
- 🔗 Integration with main FastAPI app

**Expected results**: All API endpoints should be properly configured.

### Quick Test (`python run_tests.py quick`)

**Purpose**: Fast verification that the workflow system can execute.

**What it tests**:
- ⚡ Minimal workflow execution
- 🔄 Basic task creation

**Expected results**: Should complete quickly, may show warnings if BigQuery is not configured.

## Understanding Test Results

### ✅ PASS
- Test completed successfully
- Functionality is working as expected

### ❌ FAIL
- Test failed due to an error
- Requires investigation and fixing

### ⚠️ WARN
- Test completed but with warnings
- Usually indicates missing external configuration (BigQuery, DigiKey API)
- System can still function, but with limited capabilities

## Common Test Scenarios

### Scenario 1: Fresh Installation
```bash
# Start with smoke tests to verify basic setup
python run_tests.py smoke

# If smoke tests pass, try integration tests
python run_tests.py integration
```

**Expected**: Smoke tests should pass. Integration tests may show warnings about missing BigQuery data.

### Scenario 2: BigQuery Configured
```bash
# Run integration tests to verify BigQuery connectivity
python run_tests.py integration
```

**Expected**: Should process real data from BigQuery and create tasks.

### Scenario 3: Full System with DigiKey API
```bash
# Run all tests to verify complete functionality
python run_tests.py all
```

**Expected**: All tests should pass with minimal warnings.

### Scenario 4: Production Readiness Check
```bash
# Run comprehensive tests
python run_tests.py all

# Then run a larger integration test
python run_workflow.py run --limit 10 --force-manual
python run_workflow.py pending --limit 20
```

## Troubleshooting Test Issues

### Import Errors
```
❌ Basic Imports: Import error: No module named 'src.services.workflow_orchestrator'
```

**Solution**: Ensure you're running tests from the project root directory.

### Database Connection Errors
```
❌ Database Connectivity: Database error: connection failed
```

**Solution**: 
1. Check your database configuration in `src/db/connections.py`
2. Ensure Supabase credentials are properly configured
3. Verify network connectivity

### BigQuery Warnings
```
⚠️ Small Manual Workflow: No BigQuery data available
```

**Solution**: This is normal if BigQuery is not configured. The system will still work for manual task processing.

### DigiKey API Failures
```
❌ Automation workflow failed: DigiKey API error
```

**Solution**: This is expected if DigiKey API is not configured. Automation will fall back to manual tasks.

## Test Output Files

Tests generate detailed result files:

- `smoke_test_results.json` - Detailed smoke test results
- `integration_test_results.json` - Detailed integration test results

These files contain:
- Individual test results
- Timing information
- Detailed error messages
- Test metadata

## Manual Testing

### Test CLI Commands
```bash
# Test help system
python run_workflow.py --help
python run_workflow.py run --help

# Test configuration display
python run_workflow.py config --show

# Test small workflow
python run_workflow.py run --limit 3 --force-manual

# Check results
python run_workflow.py pending --limit 10
```

### Test API Endpoints (if server is running)
```bash
# Start the API server
python src/api/app.py

# In another terminal, test endpoints
curl -X POST "http://localhost:8000/workflow/run" \
  -H "Content-Type: application/json" \
  -d '{"limit": 2, "force_manual": true}'

curl "http://localhost:8000/workflow/pending?limit=5"
```

## Performance Testing

### Baseline Performance Test
```bash
# Test with different batch sizes
python run_workflow.py run --limit 10 --force-manual
python run_workflow.py run --limit 50 --force-manual
python run_workflow.py run --limit 100 --force-manual
```

### Concurrent Processing Test
```bash
# Test automation concurrency (if DigiKey API is configured)
python run_workflow.py run --limit 20 --force-automation
```

## Continuous Testing

### Pre-deployment Checklist
1. ✅ Run smoke tests: `python run_tests.py smoke`
2. ✅ Run integration tests: `python run_tests.py integration`
3. ✅ Test CLI functionality: `python run_tests.py cli`
4. ✅ Verify API endpoints: `python run_tests.py api`
5. ✅ Run performance test: `python run_tests.py quick`

### Regular Health Checks
```bash
# Daily health check
python run_tests.py quick

# Weekly comprehensive check
python run_tests.py all
```

## Test Development

### Adding New Tests

To add new smoke tests, edit `test_workflow_smoke.py`:
```python
async def test_new_functionality(self):
    """Test new functionality."""
    try:
        # Your test code here
        self.log_test("New Functionality", "PASS", "Test passed")
    except Exception as e:
        self.log_test("New Functionality", "FAIL", f"Error: {str(e)}")
```

To add new integration tests, edit `test_workflow_integration.py`:
```python
async def test_new_integration(self):
    """Test new integration."""
    try:
        # Your integration test code here
        self.log_test("New Integration", "PASS", "Integration test passed")
    except Exception as e:
        self.log_test("New Integration", "FAIL", f"Error: {str(e)}")
```

## Best Practices

1. **Start with smoke tests** - Always run smoke tests first on new installations
2. **Run tests regularly** - Include testing in your deployment pipeline
3. **Monitor warnings** - Warnings often indicate configuration issues
4. **Test incrementally** - Start with small limits and increase gradually
5. **Keep test data** - Save test result JSON files for trend analysis
6. **Test different scenarios** - Use different configurations and data sizes

## Getting Help

If tests are failing:

1. **Check the detailed output** - Tests provide specific error messages
2. **Review the JSON result files** - Contains detailed diagnostic information
3. **Run individual test components** - Isolate the failing functionality
4. **Check system requirements** - Ensure all dependencies are installed
5. **Verify configuration** - Check database and API configurations

The testing suite is designed to help you identify and resolve issues quickly, ensuring your workflow orchestrator system is reliable and ready for production use.

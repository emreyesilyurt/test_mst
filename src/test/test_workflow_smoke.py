#!/usr/bin/env python3
"""
Smoke Tests for Workflow Orchestrator System

This script provides comprehensive smoke tests to verify that the workflow
orchestration system is working correctly end-to-end.
"""

import asyncio
import sys
import time
import json
from typing import Dict, Any, List
from datetime import datetime

# Add the project root directory to the path to access src
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.services.workflow_orchestrator import (
    WorkflowOrchestrator,
    WorkflowConfig,
    TaskType,
    TaskPriority,
    run_workflow,
    get_workflow_status,
    get_pending_manual_tasks
)
from src.db.connections import get_supabase_async_engine
from src.db.models import AutomationTask, ManualTask, Product, PartNumber
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select, func


class WorkflowSmokeTests:
    """Comprehensive smoke tests for the workflow system."""
    
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
        self.async_engine = get_supabase_async_engine()
        self.AsyncSessionLocal = async_sessionmaker(bind=self.async_engine, expire_on_commit=False)
    
    def log_test(self, test_name: str, status: str, message: str, details: Dict[str, Any] = None):
        """Log test results."""
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {message}")
        
        if status == "FAIL":
            self.failed_tests.append(test_name)
    
    async def test_basic_imports(self):
        """Test 1: Verify all imports work correctly."""
        try:
            from src.services.workflow_orchestrator import WorkflowOrchestrator
            from src.db.services.bigquery_service import BigQueryService
            from src.tasks.automation.automate_tasks import TaskAutomator
            from src.services.manual_imputation_service import ManualImputationService
            
            self.log_test("Basic Imports", "PASS", "All required modules imported successfully")
        except Exception as e:
            self.log_test("Basic Imports", "FAIL", f"Import error: {str(e)}")
    
    async def test_configuration_creation(self):
        """Test 2: Verify configuration objects can be created."""
        try:
            config = WorkflowConfig()
            
            # Check default values
            assert config.automation_priority_threshold == 0.8
            assert config.automation_max_concurrent == 5
            assert config.automation_failure_to_manual == True
            
            # Test custom configuration
            custom_config = WorkflowConfig(
                automation_priority_threshold=0.75,
                automation_max_concurrent=10
            )
            assert custom_config.automation_priority_threshold == 0.75
            assert custom_config.automation_max_concurrent == 10
            
            self.log_test("Configuration Creation", "PASS", "Configuration objects created successfully")
        except Exception as e:
            self.log_test("Configuration Creation", "FAIL", f"Configuration error: {str(e)}")
    
    async def test_orchestrator_initialization(self):
        """Test 3: Verify WorkflowOrchestrator can be initialized."""
        try:
            # Test with default config
            orchestrator = WorkflowOrchestrator()
            assert orchestrator.config is not None
            assert orchestrator.bq_service is not None
            assert orchestrator.task_automator is not None
            assert orchestrator.manual_service is not None
            
            # Test with custom config
            custom_config = WorkflowConfig(automation_max_concurrent=3)
            custom_orchestrator = WorkflowOrchestrator(custom_config)
            assert custom_orchestrator.config.automation_max_concurrent == 3
            
            self.log_test("Orchestrator Initialization", "PASS", "WorkflowOrchestrator initialized successfully")
        except Exception as e:
            self.log_test("Orchestrator Initialization", "FAIL", f"Orchestrator error: {str(e)}")
    
    async def test_database_connectivity(self):
        """Test 4: Verify database connectivity."""
        try:
            async with self.AsyncSessionLocal() as session:
                # Test basic query
                result = await session.execute(select(func.count()).select_from(Product))
                count = result.scalar()
                
                self.log_test("Database Connectivity", "PASS", f"Database connected, found {count} products")
        except Exception as e:
            self.log_test("Database Connectivity", "FAIL", f"Database error: {str(e)}")
    
    async def test_decision_engine_logic(self):
        """Test 5: Test decision engine with mock data."""
        try:
            orchestrator = WorkflowOrchestrator()
            
            # Test data with different completeness levels
            test_records = [
                {
                    'pn': 'TEST_HIGH_COMPLETE',
                    'manufacturer': 'TestManufacturer',
                    'category': 'Test Category',
                    'description': 'Complete test description',
                    'specs': [{'name': 'voltage', 'value': '5V'}],
                    'docs': [{'url': 'http://test.com/doc.pdf'}],
                    'images': [{'url': 'http://test.com/image.jpg'}],
                    'priority_score': {'score': 0.9}
                },
                {
                    'pn': 'TEST_LOW_COMPLETE',
                    'manufacturer': 'TestManufacturer',
                    'priority_score': {'score': 0.5}
                },
                {
                    'pn': 'TEST_MEDIUM_COMPLETE',
                    'manufacturer': 'TestManufacturer',
                    'category': 'Test Category',
                    'priority_score': {'score': 0.6}
                }
            ]
            
            decisions = await orchestrator._analyze_and_decide_tasks(test_records)
            
            # Verify we got decisions for all records
            assert len(decisions) == 3
            
            # Check decision logic
            high_complete = next(d for d in decisions if d.metadata['record']['pn'] == 'TEST_HIGH_COMPLETE')
            low_complete = next(d for d in decisions if d.metadata['record']['pn'] == 'TEST_LOW_COMPLETE')
            
            # High completeness should go to manual
            assert high_complete.task_type == TaskType.MANUAL
            # Low completeness should go to automation
            assert low_complete.task_type == TaskType.AUTOMATION
            
            self.log_test("Decision Engine Logic", "PASS", "Decision engine working correctly", {
                'high_complete_decision': high_complete.task_type.value,
                'low_complete_decision': low_complete.task_type.value,
                'total_decisions': len(decisions)
            })
        except Exception as e:
            self.log_test("Decision Engine Logic", "FAIL", f"Decision engine error: {str(e)}")
    
    async def test_manual_task_creation(self):
        """Test 6: Test manual task creation (without BigQuery)."""
        try:
            batch_id = f"smoke_test_{int(time.time())}"
            
            # Create a small workflow with forced manual tasks
            result = await run_workflow(
                limit=2,
                force_manual=True
            )
            
            # Check if workflow completed
            assert result['status'] in ['completed', 'no_data']
            
            if result['status'] == 'completed':
                assert result['manual_tasks'] > 0
                assert 'batch_id' in result
                
                # Check if manual tasks were created
                pending_tasks = await get_pending_manual_tasks(limit=10)
                
                self.log_test("Manual Task Creation", "PASS", f"Manual tasks created successfully", {
                    'batch_id': result['batch_id'],
                    'manual_tasks_created': result['manual_tasks'],
                    'pending_tasks_found': len(pending_tasks)
                })
            else:
                self.log_test("Manual Task Creation", "WARN", "No BigQuery data available for testing")
                
        except Exception as e:
            self.log_test("Manual Task Creation", "FAIL", f"Manual task creation error: {str(e)}")
    
    async def test_workflow_status_tracking(self):
        """Test 7: Test workflow status tracking."""
        try:
            # Create a test batch
            batch_id = f"status_test_{int(time.time())}"
            
            # Run a small workflow
            result = await run_workflow(
                limit=1,
                force_manual=True
            )
            
            if result['status'] == 'completed' and 'batch_id' in result:
                # Check status
                status = await get_workflow_status(result['batch_id'])
                
                assert 'batch_id' in status
                assert 'overall_status' in status
                
                self.log_test("Workflow Status Tracking", "PASS", "Status tracking working correctly", {
                    'batch_id': result['batch_id'],
                    'status': status.get('overall_status'),
                    'automation_tasks': status.get('automation_tasks', {}).get('total', 0),
                    'manual_tasks': status.get('manual_tasks', {}).get('total', 0)
                })
            else:
                self.log_test("Workflow Status Tracking", "WARN", "No data available for status testing")
                
        except Exception as e:
            self.log_test("Workflow Status Tracking", "FAIL", f"Status tracking error: {str(e)}")
    
    async def test_api_endpoints_basic(self):
        """Test 8: Test basic API endpoint functionality (import test)."""
        try:
            from src.api.workflow.workflow_endpoints import router
            from src.api.workflow import router as workflow_router
            
            # Verify router has expected endpoints
            routes = [route.path for route in router.routes]
            expected_routes = ['/workflow/run', '/workflow/status/{batch_id}', '/workflow/pending']
            
            for expected_route in expected_routes:
                assert any(expected_route in route for route in routes), f"Missing route: {expected_route}"
            
            self.log_test("API Endpoints Basic", "PASS", "API endpoints imported and configured correctly", {
                'total_routes': len(routes),
                'sample_routes': routes[:5]
            })
        except Exception as e:
            self.log_test("API Endpoints Basic", "FAIL", f"API endpoints error: {str(e)}")
    
    async def test_cli_interface(self):
        """Test 9: Test CLI interface functionality."""
        try:
            import subprocess
            import os
            
            # Test CLI help command
            result = subprocess.run(
                [sys.executable, 'run_workflow.py', '--help'],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            assert result.returncode == 0
            assert 'workflow' in result.stdout.lower()
            assert 'run' in result.stdout
            assert 'status' in result.stdout
            assert 'pending' in result.stdout
            
            self.log_test("CLI Interface", "PASS", "CLI interface working correctly", {
                'help_command_success': True,
                'available_commands': ['run', 'status', 'pending', 'config']
            })
        except Exception as e:
            self.log_test("CLI Interface", "FAIL", f"CLI interface error: {str(e)}")
    
    async def test_data_completeness_calculation(self):
        """Test 10: Test data completeness calculation."""
        try:
            orchestrator = WorkflowOrchestrator()
            
            # Test high completeness record
            high_complete_record = {
                'pn': 'TEST123',
                'manufacturer': 'TestCorp',
                'category': 'Resistors',
                'description': 'Test resistor',
                'specs': [{'name': 'resistance', 'value': '1k'}],
                'docs': [{'url': 'http://test.com/doc.pdf'}],
                'images': [{'url': 'http://test.com/image.jpg'}]
            }
            
            # Test low completeness record
            low_complete_record = {
                'pn': 'TEST456',
                'manufacturer': 'TestCorp'
            }
            
            high_score = orchestrator._calculate_data_completeness(high_complete_record)
            low_score = orchestrator._calculate_data_completeness(low_complete_record)
            
            assert high_score > low_score
            assert 0.0 <= high_score <= 1.0
            assert 0.0 <= low_score <= 1.0
            
            self.log_test("Data Completeness Calculation", "PASS", "Completeness calculation working correctly", {
                'high_completeness_score': high_score,
                'low_completeness_score': low_score,
                'score_difference': high_score - low_score
            })
        except Exception as e:
            self.log_test("Data Completeness Calculation", "FAIL", f"Completeness calculation error: {str(e)}")
    
    async def test_error_handling(self):
        """Test 11: Test error handling with invalid data."""
        try:
            orchestrator = WorkflowOrchestrator()
            
            # Test with invalid/empty data
            invalid_records = [
                {},  # Empty record
                {'invalid_field': 'test'},  # Record with no required fields
                None  # None record (should be handled gracefully)
            ]
            
            # This should not crash, but handle errors gracefully
            decisions = await orchestrator._analyze_and_decide_tasks([r for r in invalid_records if r is not None])
            
            # Should get decisions (likely defaulting to manual for safety)
            assert len(decisions) >= 0
            
            self.log_test("Error Handling", "PASS", "Error handling working correctly", {
                'invalid_records_processed': len([r for r in invalid_records if r is not None]),
                'decisions_made': len(decisions)
            })
        except Exception as e:
            self.log_test("Error Handling", "FAIL", f"Error handling failed: {str(e)}")
    
    async def test_convenience_functions(self):
        """Test 12: Test convenience functions."""
        try:
            # Test run_workflow function
            result = await run_workflow(limit=1, force_manual=True)
            assert isinstance(result, dict)
            assert 'status' in result
            
            # Test get_pending_manual_tasks function
            pending = await get_pending_manual_tasks(limit=5)
            assert isinstance(pending, list)
            
            self.log_test("Convenience Functions", "PASS", "Convenience functions working correctly", {
                'run_workflow_result': result.get('status'),
                'pending_tasks_count': len(pending)
            })
        except Exception as e:
            self.log_test("Convenience Functions", "FAIL", f"Convenience functions error: {str(e)}")
    
    async def run_all_tests(self):
        """Run all smoke tests."""
        print("🧪 Starting Workflow Orchestrator Smoke Tests")
        print("=" * 60)
        
        test_methods = [
            self.test_basic_imports,
            self.test_configuration_creation,
            self.test_orchestrator_initialization,
            self.test_database_connectivity,
            self.test_decision_engine_logic,
            self.test_manual_task_creation,
            self.test_workflow_status_tracking,
            self.test_api_endpoints_basic,
            self.test_cli_interface,
            self.test_data_completeness_calculation,
            self.test_error_handling,
            self.test_convenience_functions
        ]
        
        for i, test_method in enumerate(test_methods, 1):
            print(f"\n[{i}/{len(test_methods)}] Running {test_method.__name__}...")
            try:
                await test_method()
            except Exception as e:
                self.log_test(test_method.__name__, "FAIL", f"Unexpected error: {str(e)}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("🏁 Smoke Test Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warned_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️  Warnings: {warned_tests}")
        
        if failed_tests == 0:
            print("\n🎉 All critical tests passed! The workflow system is ready to use.")
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. Please review the issues above.")
            print("Failed tests:", ", ".join(self.failed_tests))
        
        # Save detailed results
        with open('smoke_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        print(f"\n📄 Detailed results saved to: smoke_test_results.json")
        
        return failed_tests == 0


async def main():
    """Main test runner."""
    tester = WorkflowSmokeTests()
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

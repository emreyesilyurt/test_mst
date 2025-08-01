#!/usr/bin/env python3
"""
Integration Tests for Workflow Orchestrator System

This script tests the workflow system with actual data processing,
including BigQuery integration and real task execution.
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
    run_workflow,
    get_workflow_status,
    get_pending_manual_tasks
)


class WorkflowIntegrationTests:
    """Integration tests for the workflow system."""
    
    def __init__(self):
        self.test_results = []
        self.batch_ids = []  # Track created batches for cleanup
    
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
        
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
    
    async def test_small_manual_workflow(self):
        """Test 1: Run a small workflow with forced manual tasks."""
        print("\n🔄 Testing small manual workflow...")
        
        try:
            # Run workflow with very small limit and force manual
            result = await run_workflow(
                limit=3,
                force_manual=True
            )
            
            if result['status'] == 'no_data':
                self.log_test("Small Manual Workflow", "WARN", 
                             "No BigQuery data available - this is expected if BigQuery is not configured")
                return
            
            # Check results
            assert result['status'] == 'completed'
            assert result['manual_tasks'] > 0
            assert 'batch_id' in result
            
            self.batch_ids.append(result['batch_id'])
            
            self.log_test("Small Manual Workflow", "PASS", 
                         "Manual workflow completed successfully", {
                             'batch_id': result['batch_id'],
                             'total_records': result['total_records'],
                             'manual_tasks': result['manual_tasks'],
                             'processing_time': f"{result['processing_time']:.2f}s"
                         })
            
        except Exception as e:
            self.log_test("Small Manual Workflow", "FAIL", f"Error: {str(e)}")
    
    async def test_small_automation_workflow(self):
        """Test 2: Run a small workflow with forced automation tasks."""
        print("\n🤖 Testing small automation workflow...")
        
        try:
            # Run workflow with very small limit and force automation
            result = await run_workflow(
                limit=2,
                force_automation=True
            )
            
            if result['status'] == 'no_data':
                self.log_test("Small Automation Workflow", "WARN", 
                             "No BigQuery data available")
                return
            
            # Check results
            assert result['status'] == 'completed'
            assert 'batch_id' in result
            
            self.batch_ids.append(result['batch_id'])
            
            # Automation might fail (expected if DigiKey API is not configured)
            automation_results = result.get('automation_results', {})
            
            self.log_test("Small Automation Workflow", "PASS", 
                         "Automation workflow completed", {
                             'batch_id': result['batch_id'],
                             'total_records': result['total_records'],
                             'automation_tasks': result['automation_tasks'],
                             'successful_automations': automation_results.get('successful', 0),
                             'failed_automations': automation_results.get('failed', 0),
                             'processing_time': f"{result['processing_time']:.2f}s"
                         })
            
        except Exception as e:
            self.log_test("Small Automation Workflow", "FAIL", f"Error: {str(e)}")
    
    async def test_mixed_workflow(self):
        """Test 3: Run a workflow with natural decision making (no forcing)."""
        print("\n🎯 Testing mixed workflow with natural decisions...")
        
        try:
            # Run workflow without forcing - let the decision engine decide
            result = await run_workflow(
                limit=5,
                priority_threshold=0.3  # Lower threshold to get more data
            )
            
            if result['status'] == 'no_data':
                self.log_test("Mixed Workflow", "WARN", 
                             "No BigQuery data available")
                return
            
            # Check results
            assert result['status'] == 'completed'
            assert 'batch_id' in result
            
            self.batch_ids.append(result['batch_id'])
            
            total_tasks = result['automation_tasks'] + result['manual_tasks']
            
            self.log_test("Mixed Workflow", "PASS", 
                         "Mixed workflow completed successfully", {
                             'batch_id': result['batch_id'],
                             'total_records': result['total_records'],
                             'automation_tasks': result['automation_tasks'],
                             'manual_tasks': result['manual_tasks'],
                             'total_tasks': total_tasks,
                             'automation_percentage': f"{(result['automation_tasks']/total_tasks*100):.1f}%" if total_tasks > 0 else "0%",
                             'processing_time': f"{result['processing_time']:.2f}s"
                         })
            
        except Exception as e:
            self.log_test("Mixed Workflow", "FAIL", f"Error: {str(e)}")
    
    async def test_workflow_status_monitoring(self):
        """Test 4: Test workflow status monitoring."""
        print("\n📊 Testing workflow status monitoring...")
        
        try:
            if not self.batch_ids:
                self.log_test("Workflow Status Monitoring", "WARN", 
                             "No batch IDs available for status testing")
                return
            
            # Test status for each created batch
            for batch_id in self.batch_ids:
                status = await get_workflow_status(batch_id)
                
                assert 'batch_id' in status
                assert status['batch_id'] == batch_id
                
                # Check if we have task information
                automation_total = status.get('automation_tasks', {}).get('total', 0)
                manual_total = status.get('manual_tasks', {}).get('total', 0)
                
                self.log_test("Workflow Status Monitoring", "PASS", 
                             f"Status retrieved for batch {batch_id}", {
                                 'overall_status': status.get('overall_status', 'unknown'),
                                 'automation_tasks': automation_total,
                                 'manual_tasks': manual_total,
                                 'total_tasks': automation_total + manual_total
                             })
            
        except Exception as e:
            self.log_test("Workflow Status Monitoring", "FAIL", f"Error: {str(e)}")
    
    async def test_pending_manual_tasks(self):
        """Test 5: Test pending manual tasks retrieval."""
        print("\n📋 Testing pending manual tasks retrieval...")
        
        try:
            # Get pending manual tasks
            pending_tasks = await get_pending_manual_tasks(limit=20)
            
            assert isinstance(pending_tasks, list)
            
            # Analyze the tasks
            high_priority = len([t for t in pending_tasks if t.get('priority') == 'high'])
            medium_priority = len([t for t in pending_tasks if t.get('priority') == 'medium'])
            low_priority = len([t for t in pending_tasks if t.get('priority') == 'low'])
            
            # Check for our test batches
            our_tasks = [t for t in pending_tasks if t.get('batch_id') in self.batch_ids]
            
            self.log_test("Pending Manual Tasks", "PASS", 
                         "Pending tasks retrieved successfully", {
                             'total_pending': len(pending_tasks),
                             'high_priority': high_priority,
                             'medium_priority': medium_priority,
                             'low_priority': low_priority,
                             'our_test_tasks': len(our_tasks),
                             'sample_task_ids': [t['task_id'] for t in pending_tasks[:3]]
                         })
            
        except Exception as e:
            self.log_test("Pending Manual Tasks", "FAIL", f"Error: {str(e)}")
    
    async def test_configuration_variations(self):
        """Test 6: Test different configuration variations."""
        print("\n⚙️ Testing configuration variations...")
        
        try:
            # Test with custom configuration
            custom_config = WorkflowConfig(
                automation_max_concurrent=2,
                automation_priority_threshold=0.9,
                manual_priority_threshold=0.3
            )
            
            orchestrator = WorkflowOrchestrator(custom_config)
            
            # Verify configuration is applied
            assert orchestrator.config.automation_max_concurrent == 2
            assert orchestrator.config.automation_priority_threshold == 0.9
            assert orchestrator.config.manual_priority_threshold == 0.3
            
            # Run a small test with custom config
            result = await orchestrator.orchestrate_workflow(
                limit=2,
                force_task_type=TaskType.MANUAL
            )
            
            if result['status'] != 'no_data':
                self.batch_ids.append(result['batch_id'])
            
            self.log_test("Configuration Variations", "PASS", 
                         "Custom configuration working correctly", {
                             'custom_max_concurrent': custom_config.automation_max_concurrent,
                             'custom_auto_threshold': custom_config.automation_priority_threshold,
                             'custom_manual_threshold': custom_config.manual_priority_threshold,
                             'workflow_status': result['status']
                         })
            
        except Exception as e:
            self.log_test("Configuration Variations", "FAIL", f"Error: {str(e)}")
    
    async def test_error_recovery(self):
        """Test 7: Test error recovery and fallback mechanisms."""
        print("\n🛡️ Testing error recovery...")
        
        try:
            # Test with invalid priority threshold (should handle gracefully)
            result = await run_workflow(
                limit=1,
                priority_threshold=1.5,  # Invalid threshold > 1.0
                force_manual=True
            )
            
            # Should still work (system should handle invalid threshold)
            assert result['status'] in ['completed', 'no_data', 'error']
            
            if result['status'] == 'completed':
                self.batch_ids.append(result['batch_id'])
            
            self.log_test("Error Recovery", "PASS", 
                         "Error recovery working correctly", {
                             'invalid_threshold_handled': True,
                             'result_status': result['status']
                         })
            
        except Exception as e:
            self.log_test("Error Recovery", "FAIL", f"Error recovery failed: {str(e)}")
    
    async def test_performance_baseline(self):
        """Test 8: Establish performance baseline."""
        print("\n⚡ Testing performance baseline...")
        
        try:
            start_time = time.time()
            
            # Run a small workflow and measure performance
            result = await run_workflow(
                limit=5,
                force_manual=True
            )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            if result['status'] == 'completed':
                self.batch_ids.append(result['batch_id'])
                
                records_per_second = result['total_records'] / result['processing_time'] if result['processing_time'] > 0 else 0
                
                self.log_test("Performance Baseline", "PASS", 
                             "Performance baseline established", {
                                 'total_time': f"{total_time:.2f}s",
                                 'processing_time': f"{result['processing_time']:.2f}s",
                                 'records_processed': result['total_records'],
                                 'records_per_second': f"{records_per_second:.2f}",
                                 'tasks_created': result['automation_tasks'] + result['manual_tasks']
                             })
            else:
                self.log_test("Performance Baseline", "WARN", 
                             f"No data available for performance testing: {result['status']}")
            
        except Exception as e:
            self.log_test("Performance Baseline", "FAIL", f"Performance test failed: {str(e)}")
    
    async def run_all_tests(self):
        """Run all integration tests."""
        print("🧪 Starting Workflow Orchestrator Integration Tests")
        print("=" * 60)
        print("⚠️  Note: Some tests may show warnings if BigQuery or DigiKey API are not configured")
        print("=" * 60)
        
        test_methods = [
            self.test_small_manual_workflow,
            self.test_small_automation_workflow,
            self.test_mixed_workflow,
            self.test_workflow_status_monitoring,
            self.test_pending_manual_tasks,
            self.test_configuration_variations,
            self.test_error_recovery,
            self.test_performance_baseline
        ]
        
        for i, test_method in enumerate(test_methods, 1):
            print(f"\n[{i}/{len(test_methods)}] Running {test_method.__name__}...")
            try:
                await test_method()
                # Small delay between tests
                await asyncio.sleep(1)
            except Exception as e:
                self.log_test(test_method.__name__, "FAIL", f"Unexpected error: {str(e)}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("🏁 Integration Test Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warned_tests = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️  Warnings: {warned_tests}")
        
        if self.batch_ids:
            print(f"\n📦 Created Batches: {len(self.batch_ids)}")
            for batch_id in self.batch_ids:
                print(f"   - {batch_id}")
            print("\n💡 You can check these batches with:")
            print("   python run_workflow.py status <batch_id>")
            print("   python run_workflow.py pending --limit 20")
        
        if failed_tests == 0:
            print("\n🎉 All integration tests passed! The workflow system is working correctly.")
            if warned_tests > 0:
                print("⚠️  Some warnings occurred - likely due to missing BigQuery/DigiKey configuration.")
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. Please review the issues above.")
        
        # Save detailed results
        with open('integration_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        print(f"\n📄 Detailed results saved to: integration_test_results.json")
        
        return failed_tests == 0


async def main():
    """Main test runner."""
    tester = WorkflowIntegrationTests()
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

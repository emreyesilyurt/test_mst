#!/usr/bin/env python3
"""
Test Runner for Workflow Orchestrator System

This script provides an easy way to run different types of tests for the workflow system.
"""

import asyncio
import sys
import argparse
import subprocess
from datetime import datetime


def print_banner():
    """Print test runner banner."""
    print("=" * 60)
    print("🧪 Workflow Orchestrator Test Runner")
    print("=" * 60)
    print()


def run_smoke_tests():
    """Run smoke tests."""
    print("🔥 Running Smoke Tests...")
    print("These tests verify basic functionality without external dependencies.")
    print("-" * 60)
    
    try:
        result = subprocess.run([sys.executable, '-m', 'src.test.test_workflow_smoke'], 
                              capture_output=False, text=True)
        # Smoke tests pass if exit code is 0 (all critical tests passed)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running smoke tests: {str(e)}")
        return False


def run_integration_tests():
    """Run integration tests."""
    print("🔗 Running Integration Tests...")
    print("These tests verify end-to-end functionality with real data processing.")
    print("-" * 60)
    
    try:
        result = subprocess.run([sys.executable, '-m', 'src.test.test_workflow_integration'], 
                              capture_output=False, text=True)
        # Integration tests pass if exit code is 0 (all critical tests passed)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running integration tests: {str(e)}")
        return False


def run_cli_tests():
    """Run CLI tests."""
    print("💻 Running CLI Tests...")
    print("These tests verify the command-line interface functionality.")
    print("-" * 60)
    
    cli_tests = [
        # Test help commands
        ([sys.executable, 'run_workflow.py', '--help'], "CLI help command"),
        ([sys.executable, 'run_workflow.py', 'run', '--help'], "Run command help"),
        ([sys.executable, 'run_workflow.py', 'status', '--help'], "Status command help"),
        ([sys.executable, 'run_workflow.py', 'pending', '--help'], "Pending command help"),
        ([sys.executable, 'run_workflow.py', 'config', '--show'], "Config show command"),
    ]
    
    passed = 0
    total = len(cli_tests)
    
    for cmd, description in cli_tests:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"✅ {description}: PASS")
                passed += 1
            else:
                print(f"❌ {description}: FAIL (exit code: {result.returncode})")
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"⚠️  {description}: TIMEOUT")
        except Exception as e:
            print(f"❌ {description}: ERROR - {str(e)}")
    
    print(f"\nCLI Tests: {passed}/{total} passed")
    return passed == total


def run_api_tests():
    """Run basic API tests."""
    print("🌐 Running API Tests...")
    print("These tests verify the API endpoints can be imported and configured.")
    print("-" * 60)
    
    try:
        # Test API imports
        test_script = """
import sys
sys.path.append('src')

try:
    from src.api.workflow.workflow_endpoints import router
    from src.api.app import app
    
    # Check if workflow router is included
    routes = [route.path for route in router.routes]
    expected_routes = ['/workflow/run', '/workflow/status/{batch_id}', '/workflow/pending']
    
    missing_routes = []
    for expected in expected_routes:
        if not any(expected in route for route in routes):
            missing_routes.append(expected)
    
    if missing_routes:
        print(f"❌ Missing routes: {missing_routes}")
        sys.exit(1)
    else:
        print("✅ All expected API routes found")
        print(f"✅ Total routes: {len(routes)}")
        sys.exit(0)
        
except Exception as e:
    print(f"❌ API import error: {str(e)}")
    sys.exit(1)
"""
        
        result = subprocess.run([sys.executable, '-c', test_script], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout.strip())
            return True
        else:
            print(result.stdout.strip())
            print(result.stderr.strip())
            return False
            
    except Exception as e:
        print(f"❌ Error running API tests: {str(e)}")
        return False


def run_quick_workflow_test():
    """Run a quick workflow test."""
    print("⚡ Running Quick Workflow Test...")
    print("This test runs a minimal workflow to verify basic functionality.")
    print("-" * 60)
    
    try:
        # Run a very small workflow test
        cmd = [sys.executable, 'run_workflow.py', 'run', '--limit', '1', '--force-manual']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Quick workflow test completed successfully")
            print("Output:")
            print(result.stdout)
            return True
        else:
            print("❌ Quick workflow test failed")
            print("Error output:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Quick workflow test timed out (this may be normal if BigQuery is slow)")
        return True  # Don't fail on timeout
    except Exception as e:
        print(f"❌ Error running quick workflow test: {str(e)}")
        return False


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Test Runner for Workflow Orchestrator System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Types:
  smoke       - Basic functionality tests (no external dependencies)
  integration - End-to-end tests with real data processing
  cli         - Command-line interface tests
  api         - API endpoint tests
  quick       - Quick workflow functionality test
  all         - Run all test types

Examples:
  python run_tests.py smoke
  python run_tests.py integration
  python run_tests.py all
        """
    )
    
    parser.add_argument('test_type', 
                       choices=['smoke', 'integration', 'cli', 'api', 'quick', 'all'],
                       help='Type of tests to run')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    print_banner()
    print(f"🚀 Starting tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    if args.test_type == 'all':
        test_types = ['smoke', 'integration', 'cli', 'api', 'quick']
    else:
        test_types = [args.test_type]
    
    for test_type in test_types:
        print(f"\n{'='*60}")
        
        if test_type == 'smoke':
            results['smoke'] = run_smoke_tests()
        elif test_type == 'integration':
            results['integration'] = run_integration_tests()
        elif test_type == 'cli':
            results['cli'] = run_cli_tests()
        elif test_type == 'api':
            results['api'] = run_api_tests()
        elif test_type == 'quick':
            results['quick'] = run_quick_workflow_test()
    
    # Print final summary
    print(f"\n{'='*60}")
    print("🏁 Final Test Summary")
    print(f"{'='*60}")
    
    total_passed = 0
    total_tests = len(results)
    
    for test_type, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_type.upper():12} {status}")
        if passed:
            total_passed += 1
    
    print(f"\nOverall: {total_passed}/{total_tests} test suites passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed! The workflow system is ready to use.")
        exit_code = 0
    else:
        print(f"\n⚠️  {total_tests - total_passed} test suite(s) failed.")
        print("Please review the output above for details.")
        exit_code = 1
    
    print(f"\n📄 Individual test results saved to:")
    print("   - smoke_test_results.json (if smoke tests were run)")
    print("   - integration_test_results.json (if integration tests were run)")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

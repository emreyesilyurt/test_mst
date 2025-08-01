#!/usr/bin/env python3
"""
Workflow Orchestrator CLI Script for master_electronics.

This script provides a command-line interface to run the workflow orchestration
system that fetches data from BigQuery and delegates tasks to automation or manual processes.
"""

import asyncio
import argparse
import sys
import json
from datetime import datetime
from typing import Optional

# Add the src directory to the path
sys.path.append('src')

from src.services.workflow_orchestrator import (
    run_workflow, 
    get_workflow_status, 
    get_pending_manual_tasks,
    WorkflowOrchestrator,
    WorkflowConfig
)


def print_banner():
    """Print a nice banner for the CLI."""
    print("=" * 60)
    print("🔄 Master Electronics Workflow Orchestrator")
    print("=" * 60)
    print()


def print_results(results: dict):
    """Print workflow results in a nice format."""
    print("\n📊 Workflow Results:")
    print("-" * 40)
    print(f"Batch ID: {results.get('batch_id', 'N/A')}")
    print(f"Status: {results.get('status', 'N/A')}")
    print(f"Total Records: {results.get('total_records', 0)}")
    print(f"Processing Time: {results.get('processing_time', 0):.2f} seconds")
    
    if results.get('automation_tasks', 0) > 0:
        print(f"\n🤖 Automation Tasks: {results['automation_tasks']}")
        if results.get('automation_results'):
            auto_results = results['automation_results']
            print(f"   ✅ Successful: {auto_results.get('successful', 0)}")
            print(f"   ❌ Failed: {auto_results.get('failed', 0)}")
            if auto_results.get('errors'):
                print(f"   📝 Sample errors:")
                for error in auto_results['errors'][:3]:  # Show first 3 errors
                    print(f"      - {error['part_number']}: {error['error'][:50]}...")
    
    if results.get('manual_tasks', 0) > 0:
        print(f"\n👤 Manual Tasks: {results['manual_tasks']}")
        if results.get('manual_results'):
            manual_results = results['manual_results']
            print(f"   ✅ Created: {manual_results.get('successful', 0)}")
            print(f"   ❌ Failed: {manual_results.get('failed', 0)}")
            if manual_results.get('task_ids'):
                print(f"   📋 Task IDs: {manual_results['task_ids'][:5]}...")  # Show first 5
    
    if results.get('fallback_results'):
        fallback_results = results['fallback_results']
        print(f"\n🔄 Fallback Tasks: {fallback_results.get('successful', 0)}")


def print_status(status: dict):
    """Print workflow status in a nice format."""
    print("\n📈 Workflow Status:")
    print("-" * 40)
    print(f"Batch ID: {status.get('batch_id', 'N/A')}")
    print(f"Overall Status: {status.get('overall_status', 'N/A')}")
    
    if status.get('automation_tasks'):
        auto_tasks = status['automation_tasks']
        print(f"\n🤖 Automation Tasks: {auto_tasks.get('total', 0)}")
        if auto_tasks.get('status_breakdown'):
            for status_name, count in auto_tasks['status_breakdown'].items():
                print(f"   {status_name}: {count}")
    
    if status.get('manual_tasks'):
        manual_tasks = status['manual_tasks']
        print(f"\n👤 Manual Tasks: {manual_tasks.get('total', 0)}")
        if manual_tasks.get('status_breakdown'):
            for status_name, count in manual_tasks['status_breakdown'].items():
                print(f"   {status_name}: {count}")


def print_pending_tasks(tasks: list):
    """Print pending manual tasks in a nice format."""
    print(f"\n📋 Pending Manual Tasks ({len(tasks)}):")
    print("-" * 60)
    
    if not tasks:
        print("No pending manual tasks found.")
        return
    
    for task in tasks:
        print(f"Task ID: {task['task_id']}")
        print(f"  Part Number: {task['part_number'] or 'N/A'}")
        print(f"  Priority: {task['priority']}")
        print(f"  Status: {task['current_status']}")
        print(f"  Batch: {task['batch_id']}")
        print(f"  Created: {task['created_date']}")
        print(f"  Note: {task['note'][:50] if task['note'] else 'N/A'}...")
        print()


async def run_workflow_command(args):
    """Run the workflow orchestration."""
    print_banner()
    print(f"🚀 Starting workflow with {args.limit} records...")
    
    if args.force_automation and args.force_manual:
        print("❌ Error: Cannot force both automation and manual modes.")
        return
    
    try:
        results = await run_workflow(
            limit=args.limit,
            priority_threshold=args.priority_threshold,
            force_automation=args.force_automation,
            force_manual=args.force_manual
        )
        
        print_results(results)
        
        # Save results to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")
        
        # Show batch ID for status checking
        if results.get('batch_id'):
            print(f"\n🔍 To check status later, run:")
            print(f"python run_workflow.py status {results['batch_id']}")
        
    except Exception as e:
        print(f"❌ Error running workflow: {str(e)}")
        sys.exit(1)


async def status_command(args):
    """Check workflow status."""
    print_banner()
    print(f"🔍 Checking status for batch: {args.batch_id}")
    
    try:
        status = await get_workflow_status(args.batch_id)
        print_status(status)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(status, f, indent=2, default=str)
            print(f"\n💾 Status saved to {args.output}")
        
    except Exception as e:
        print(f"❌ Error checking status: {str(e)}")
        sys.exit(1)


async def pending_command(args):
    """Show pending manual tasks."""
    print_banner()
    print(f"📋 Getting pending manual tasks (limit: {args.limit})...")
    
    try:
        tasks = await get_pending_manual_tasks(
            limit=args.limit,
            priority=args.priority
        )
        
        print_pending_tasks(tasks)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(tasks, f, indent=2, default=str)
            print(f"\n💾 Tasks saved to {args.output}")
        
    except Exception as e:
        print(f"❌ Error getting pending tasks: {str(e)}")
        sys.exit(1)


async def config_command(args):
    """Show or modify workflow configuration."""
    print_banner()
    
    if args.show:
        print("⚙️  Current Workflow Configuration:")
        print("-" * 40)
        config = WorkflowConfig()
        print(f"Automation Priority Threshold: {config.automation_priority_threshold}")
        print(f"Manual Priority Threshold: {config.manual_priority_threshold}")
        print(f"Max Concurrent Automation: {config.automation_max_concurrent}")
        print(f"Max Automation Failures: {config.max_automation_failures}")
        print(f"Automation Failure to Manual: {config.automation_failure_to_manual}")
        print(f"Max Daily Tasks: {config.max_daily_tasks}")
        print(f"Max Batch Size: {config.max_batch_size}")
    else:
        print("⚙️  Configuration modification not implemented yet.")
        print("Edit the WorkflowConfig class in src/services/workflow_orchestrator.py")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Master Electronics Workflow Orchestrator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run workflow with 50 records
  python run_workflow.py run --limit 50
  
  # Force all tasks to manual mode
  python run_workflow.py run --limit 20 --force-manual
  
  # Check status of a batch
  python run_workflow.py status batch_1234567890
  
  # Get pending manual tasks
  python run_workflow.py pending --limit 10 --priority high
  
  # Show current configuration
  python run_workflow.py config --show
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run workflow command
    run_parser = subparsers.add_parser('run', help='Run workflow orchestration')
    run_parser.add_argument('--limit', type=int, default=100, 
                           help='Maximum number of records to process (default: 100)')
    run_parser.add_argument('--priority-threshold', type=float,
                           help='Override priority threshold for BigQuery filtering')
    run_parser.add_argument('--force-automation', action='store_true',
                           help='Force all tasks to automation mode')
    run_parser.add_argument('--force-manual', action='store_true',
                           help='Force all tasks to manual mode')
    run_parser.add_argument('--output', type=str,
                           help='Save results to JSON file')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check workflow status')
    status_parser.add_argument('batch_id', help='Batch ID to check status for')
    status_parser.add_argument('--output', type=str,
                              help='Save status to JSON file')
    
    # Pending tasks command
    pending_parser = subparsers.add_parser('pending', help='Show pending manual tasks')
    pending_parser.add_argument('--limit', type=int, default=50,
                               help='Maximum number of tasks to show (default: 50)')
    pending_parser.add_argument('--priority', choices=['high', 'medium', 'low'],
                               help='Filter by priority')
    pending_parser.add_argument('--output', type=str,
                               help='Save tasks to JSON file')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Show or modify configuration')
    config_parser.add_argument('--show', action='store_true',
                              help='Show current configuration')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Run the appropriate command
    try:
        if args.command == 'run':
            asyncio.run(run_workflow_command(args))
        elif args.command == 'status':
            asyncio.run(status_command(args))
        elif args.command == 'pending':
            asyncio.run(pending_command(args))
        elif args.command == 'config':
            asyncio.run(config_command(args))
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

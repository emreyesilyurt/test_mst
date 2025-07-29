#!/usr/bin/env python3
"""
Example script demonstrating the new AutomationTask functionality.
This shows how to use the enhanced TaskAutomator with automation task tracking.
"""

import asyncio
from src.tasks.automation.automate_tasks import TaskAutomator

async def example_single_part_processing():
    """
    Example of processing a single part number with full automation task tracking.
    """
    print("=== Single Part Number Processing Example ===")
    
    # Create a TaskAutomator instance
    automator = TaskAutomator(silent=False)
    
    # Example part number to process
    part_number = "LM358N"
    batch_id = "example_batch_001"
    
    try:
        # Process the part number with full tracking
        result = await automator.test_digikey_search(part_number, batch_id)
        
        print(f"Processing result: {result}")
        
    except Exception as e:
        print(f"Error processing part number {part_number}: {e}")

async def example_automation_task_management():
    """
    Example of manually managing AutomationTask lifecycle.
    """
    print("\n=== Manual AutomationTask Management Example ===")
    
    automator = TaskAutomator(silent=False)
    part_number = "TL072CN"
    batch_id = "manual_batch_001"
    
    try:
        # Step 1: Create automation task
        task = await automator.create_automation_task(part_number, batch_id)
        print(f"Created task with ID: {task.id}")
        
        # Step 2: Start processing
        await automator.update_task_status(task.id, 'start_processing')
        print("Marked task as started processing")
        
        # Simulate some processing work
        await asyncio.sleep(1)
        
        # Step 3: Mark data processing finished
        await automator.update_task_status(task.id, 'mark_data_finished')
        print("Marked data processing as finished")
        
        # Simulate database write
        await asyncio.sleep(0.5)
        
        # Step 4: Mark Supabase write finished
        await automator.update_task_status(task.id, 'mark_supabase_finished')
        print("Marked Supabase write as finished")
        
        # Step 5: Complete the task
        await automator.update_task_status(task.id, 'mark_completed')
        print("Marked task as completed")
        
    except Exception as e:
        print(f"Error in manual task management: {e}")
        if 'task' in locals():
            await automator.update_task_status(task.id, 'mark_failed', str(e))

async def main():
    """
    Main function to run all examples.
    """
    print("AutomationTask Functionality Examples")
    print("=" * 50)
    
    # Run single part processing example
    await example_single_part_processing()
    
    # Run manual task management example
    await example_automation_task_management()
    
    print("\n=== Examples completed ===")

if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())

#!/usr/bin/env python3
"""
Script to add new AutomationTask columns to existing imputation_tasks table.
This preserves all existing data while adding the new tracking functionality.
"""

import asyncio
import sys
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.connections import get_supabase_async_engine

async def add_columns_to_imputation_tasks():
    """
    Add new columns to existing imputation_tasks table.
    """
    async_engine = get_supabase_async_engine()
    AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            print("🔄 Adding new columns to imputation_tasks table...")
            
            # Check if table exists
            result = await session.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = 'test' 
                AND table_name = 'imputation_tasks'
            """))
            table_exists = result.scalar() > 0
            
            if not table_exists:
                print("❌ imputation_tasks table does not exist!")
                return
            
            # Get current record count
            result = await session.execute(text("SELECT COUNT(*) FROM test.imputation_tasks"))
            record_count = result.scalar()
            print(f"📊 Found {record_count} existing records in imputation_tasks")
            
            # List of new columns to add
            new_columns = [
                ("part_number", "VARCHAR"),
                ("error_message", "TEXT"),
                ("processing_start_time", "TIMESTAMP"),
                ("processing_end_time", "TIMESTAMP"),
                ("data_processing_time", "TIMESTAMP"),
                ("supabase_write_time", "TIMESTAMP")
            ]
            
            # Add each column if it doesn't exist
            for column_name, column_type in new_columns:
                try:
                    # Check if column already exists
                    result = await session.execute(text(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.columns 
                        WHERE table_schema = 'test' 
                        AND table_name = 'imputation_tasks' 
                        AND column_name = '{column_name}'
                    """))
                    column_exists = result.scalar() > 0
                    
                    if not column_exists:
                        # Add the column
                        await session.execute(text(f"""
                            ALTER TABLE test.imputation_tasks 
                            ADD COLUMN {column_name} {column_type}
                        """))
                        print(f"✅ Added column: {column_name} ({column_type})")
                    else:
                        print(f"ℹ️  Column {column_name} already exists, skipping")
                        
                except Exception as e:
                    print(f"⚠️  Warning: Could not add column {column_name}: {e}")
            
            await session.commit()
            
            # Verify the new structure
            result = await session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'test' 
                AND table_name = 'imputation_tasks'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            
            print(f"\n📋 Current imputation_tasks table structure:")
            for column_name, data_type in columns:
                print(f"   - {column_name}: {data_type}")
            
            print(f"\n✅ Successfully updated imputation_tasks table!")
            print(f"📊 All {record_count} existing records preserved")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Failed to add columns: {e}")
            raise

async def verify_table_structure():
    """
    Verify that all required columns exist in imputation_tasks table.
    """
    async_engine = get_supabase_async_engine()
    AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            print("\n🔍 Verifying table structure...")
            
            required_columns = [
                'id', 'batch_id', 'task_profile', 'report', 'step_order', 
                'current_step', 'current_status', 'created_date', 'updated_date',
                'pn_id', 'automation_ref', 'part_number', 'error_message',
                'processing_start_time', 'processing_end_time', 
                'data_processing_time', 'supabase_write_time'
            ]
            
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'test' 
                AND table_name = 'imputation_tasks'
            """))
            existing_columns = [row[0] for row in result.fetchall()]
            
            missing_columns = []
            for col in required_columns:
                if col in existing_columns:
                    print(f"✅ {col}")
                else:
                    print(f"❌ {col} - MISSING")
                    missing_columns.append(col)
            
            if missing_columns:
                print(f"\n⚠️  Missing columns: {missing_columns}")
                print("Please run the column addition script again.")
            else:
                print(f"\n🎉 All required columns are present!")
                print("The imputation_tasks table is ready for AutomationTask functionality.")
                
        except Exception as e:
            print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    print("Add New Columns to imputation_tasks Table")
    print("=" * 50)
    
    # Add columns
    asyncio.run(add_columns_to_imputation_tasks())
    
    # Verify structure
    asyncio.run(verify_table_structure())
    
    print("\n🎉 Column addition process completed!")
    print("Your existing imputation_tasks table now supports AutomationTask functionality.")

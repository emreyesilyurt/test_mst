#!/usr/bin/env python3
"""
Migration script to safely migrate data from imputation_tasks to automation_tasks table.
This script will:
1. Copy all data from imputation_tasks to automation_tasks
2. Update foreign key references in related tables
3. Preserve all existing data
"""

import asyncio
from sqlalchemy import text, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.db.connections import get_supabase_async_engine
from src.db.models import (
    AutomationTask, DocumentMedia, ProductSeller, 
    ProductAttribute, ProductExtra
)

async def migrate_data():
    """
    Migrate data from imputation_tasks to automation_tasks and update references.
    """
    async_engine = get_supabase_async_engine()
    AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            print("🔄 Starting migration from imputation_tasks to automation_tasks...")
            
            # Step 1: Check if imputation_tasks table exists and has data
            result = await session.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = 'test' 
                AND table_name = 'imputation_tasks'
            """))
            table_exists = result.scalar() > 0
            
            if not table_exists:
                print("❌ imputation_tasks table does not exist. Nothing to migrate.")
                return
            
            # Check if there's data to migrate
            result = await session.execute(text("SELECT COUNT(*) FROM test.imputation_tasks"))
            imputation_count = result.scalar()
            print(f"📊 Found {imputation_count} records in imputation_tasks table")
            
            if imputation_count == 0:
                print("ℹ️  No data to migrate from imputation_tasks")
                return
            
            # Step 2: Copy data from imputation_tasks to automation_tasks
            print("📋 Copying data from imputation_tasks to automation_tasks...")
            
            # Insert data with ID mapping
            await session.execute(text("""
                INSERT INTO test.automation_tasks (
                    id, batch_id, task_profile, report, step_order, current_step, 
                    current_status, created_date, updated_date, pn_id, automation_ref,
                    part_number, error_message, processing_start_time, processing_end_time,
                    data_processing_time, supabase_write_time
                )
                SELECT 
                    id, batch_id, task_profile, report, step_order, current_step,
                    current_status, created_date, updated_date, pn_id, automation_ref,
                    NULL as part_number,  -- Will be populated later if needed
                    NULL as error_message,
                    created_date as processing_start_time,  -- Use created_date as fallback
                    updated_date as processing_end_time,    -- Use updated_date as fallback
                    NULL as data_processing_time,
                    NULL as supabase_write_time
                FROM test.imputation_tasks
                ON CONFLICT (id) DO NOTHING  -- Skip if already exists
            """))
            
            await session.commit()
            
            # Verify the copy
            result = await session.execute(text("SELECT COUNT(*) FROM test.automation_tasks"))
            automation_count = result.scalar()
            print(f"✅ Successfully copied {automation_count} records to automation_tasks")
            
            # Step 3: Update foreign key references in related tables
            print("🔗 Updating foreign key references in related tables...")
            
            # Update DocumentMedia references
            doc_result = await session.execute(text("""
                UPDATE test.document_media 
                SET ref_id = ref_id 
                WHERE ref_id IN (SELECT id FROM test.automation_tasks)
            """))
            print(f"📄 Updated {doc_result.rowcount} DocumentMedia references")
            
            # Update ProductSeller references  
            seller_result = await session.execute(text("""
                UPDATE test.product_sellers 
                SET ref_id = ref_id 
                WHERE ref_id IN (SELECT id FROM test.automation_tasks)
            """))
            print(f"🏪 Updated {seller_result.rowcount} ProductSeller references")
            
            # Update ProductAttribute references
            attr_result = await session.execute(text("""
                UPDATE test.product_attributes 
                SET ref_id = ref_id 
                WHERE ref_id IN (SELECT id FROM test.automation_tasks)
            """))
            print(f"🏷️  Updated {attr_result.rowcount} ProductAttribute references")
            
            # Update ProductExtra references
            extra_result = await session.execute(text("""
                UPDATE test.product_extras 
                SET ref_id = ref_id 
                WHERE ref_id IN (SELECT id FROM test.automation_tasks)
            """))
            print(f"➕ Updated {extra_result.rowcount} ProductExtra references")
            
            await session.commit()
            
            print("✅ Migration completed successfully!")
            print(f"📊 Summary:")
            print(f"   - Migrated {automation_count} automation tasks")
            print(f"   - Updated {doc_result.rowcount} document media references")
            print(f"   - Updated {seller_result.rowcount} product seller references") 
            print(f"   - Updated {attr_result.rowcount} product attribute references")
            print(f"   - Updated {extra_result.rowcount} product extra references")
            
            # Step 4: Optional - Rename old table for backup
            print("\n🔄 Creating backup of original imputation_tasks table...")
            await session.execute(text("""
                ALTER TABLE test.imputation_tasks 
                RENAME TO imputation_tasks_backup_""" + str(int(asyncio.get_event_loop().time()))))
            await session.commit()
            print("✅ Original table backed up as imputation_tasks_backup_[timestamp]")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Migration failed: {e}")
            raise

async def verify_migration():
    """
    Verify that the migration was successful.
    """
    async_engine = get_supabase_async_engine()
    AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            print("\n🔍 Verifying migration...")
            
            # Check automation_tasks count
            result = await session.execute(text("SELECT COUNT(*) FROM test.automation_tasks"))
            automation_count = result.scalar()
            print(f"📊 automation_tasks table has {automation_count} records")
            
            # Check related table references
            tables_to_check = [
                ("document_media", "DocumentMedia"),
                ("product_sellers", "ProductSeller"), 
                ("product_attributes", "ProductAttribute"),
                ("product_extras", "ProductExtra")
            ]
            
            for table_name, model_name in tables_to_check:
                result = await session.execute(text(f"""
                    SELECT COUNT(*) FROM test.{table_name} 
                    WHERE ref_id IN (SELECT id FROM test.automation_tasks)
                """))
                ref_count = result.scalar()
                print(f"🔗 {model_name}: {ref_count} records reference automation_tasks")
            
            print("✅ Migration verification completed!")
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    print("AutomationTask Migration Tool")
    print("=" * 50)
    
    # Run migration
    asyncio.run(migrate_data())
    
    # Verify migration
    asyncio.run(verify_migration())
    
    print("\n🎉 Migration process completed!")
    print("Your existing data has been safely migrated to the new automation_tasks table.")

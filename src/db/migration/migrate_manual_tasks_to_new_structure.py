"""
Migration script to update the existing manual_tasks table structure
to match the new AutomationTask-like structure.

This script will:
1. Add new columns that don't exist
2. Migrate data from old columns to new columns
3. Drop old columns that are no longer needed
"""

import asyncio
from sqlalchemy import text, MetaData, Table, inspect
from sqlalchemy.ext.asyncio import create_async_engine
from src.db.connections import get_supabase_async_engine


async def migrate_manual_tasks_table():
    """
    Migrate the manual_tasks table to the new structure.
    """
    engine = get_supabase_async_engine()
    
    async with engine.begin() as conn:
        # First, let's check what columns currently exist
        print("🔍 Checking current table structure...")
        
        # Get current columns
        result = await conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'production' 
            AND table_name = 'manual_tasks'
            ORDER BY ordinal_position;
        """))
        
        current_columns = {row[0]: {'type': row[1], 'nullable': row[2]} for row in result.fetchall()}
        print(f"Current columns: {list(current_columns.keys())}")
        
        # Define the migration steps
        migration_steps = []
        
        # Step 1: Add new columns if they don't exist
        new_columns = {
            'current_status': "ALTER TABLE production.manual_tasks ADD COLUMN current_status TEXT DEFAULT 'completed';",
            'error_message': "ALTER TABLE production.manual_tasks ADD COLUMN error_message TEXT;",
            'processing_info': "ALTER TABLE production.manual_tasks ADD COLUMN processing_info JSONB;",
            'created_date': "ALTER TABLE production.manual_tasks ADD COLUMN created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW();",
            'updated_date': "ALTER TABLE production.manual_tasks ADD COLUMN updated_date TIMESTAMP WITH TIME ZONE DEFAULT NOW();"
        }
        
        for col_name, sql in new_columns.items():
            if col_name not in current_columns:
                migration_steps.append(f"Adding column {col_name}")
                await conn.execute(text(sql))
                print(f"✅ Added column: {col_name}")
        
        # Step 2: Migrate data from old columns to new columns
        print("\n📊 Migrating data from old columns to new columns...")
        
        # Migrate created_at to created_date if both exist
        if 'created_at' in current_columns and 'created_date' in current_columns:
            await conn.execute(text("""
                UPDATE production.manual_tasks 
                SET created_date = created_at 
                WHERE created_date IS NULL AND created_at IS NOT NULL;
            """))
            print("✅ Migrated created_at → created_date")
        
        # Migrate updated_at to updated_date if both exist
        if 'updated_at' in current_columns and 'updated_date' in current_columns:
            await conn.execute(text("""
                UPDATE production.manual_tasks 
                SET updated_date = updated_at 
                WHERE updated_date IS NULL AND updated_at IS NOT NULL;
            """))
            print("✅ Migrated updated_at → updated_date")
        
        # Migrate status to current_status if both exist
        if 'status' in current_columns and 'current_status' in current_columns:
            await conn.execute(text("""
                UPDATE production.manual_tasks 
                SET current_status = COALESCE(status, 'completed')
                WHERE current_status = 'completed';
            """))
            print("✅ Migrated status → current_status")
        
        # Create processing_info from existing timing columns
        if 'processing_start_time' in current_columns and 'processing_end_time' in current_columns:
            await conn.execute(text("""
                UPDATE production.manual_tasks 
                SET processing_info = jsonb_build_object(
                    'start_time', processing_start_time::text,
                    'end_time', processing_end_time::text,
                    'current_step', 'finished'
                )
                WHERE processing_info IS NULL 
                AND (processing_start_time IS NOT NULL OR processing_end_time IS NOT NULL);
            """))
            print("✅ Created processing_info from timing columns")
        
        # Step 3: Set default values for required fields
        print("\n🔧 Setting default values for required fields...")
        
        # Ensure all records have a current_status
        await conn.execute(text("""
            UPDATE production.manual_tasks 
            SET current_status = 'completed' 
            WHERE current_status IS NULL;
        """))
        
        # Ensure all records have created_date
        await conn.execute(text("""
            UPDATE production.manual_tasks 
            SET created_date = NOW() 
            WHERE created_date IS NULL;
        """))
        
        # Ensure all records have updated_date
        await conn.execute(text("""
            UPDATE production.manual_tasks 
            SET updated_date = COALESCE(created_date, NOW()) 
            WHERE updated_date IS NULL;
        """))
        
        print("✅ Set default values for required fields")
        
        # Step 4: Add constraints
        print("\n🔒 Adding constraints...")
        
        # Make current_status NOT NULL
        if 'current_status' not in current_columns or current_columns['current_status']['nullable'] == 'YES':
            await conn.execute(text("""
                ALTER TABLE production.manual_tasks 
                ALTER COLUMN current_status SET NOT NULL;
            """))
            print("✅ Made current_status NOT NULL")
        
        # Make created_date NOT NULL
        if 'created_date' not in current_columns or current_columns['created_date']['nullable'] == 'YES':
            await conn.execute(text("""
                ALTER TABLE production.manual_tasks 
                ALTER COLUMN created_date SET NOT NULL;
            """))
            print("✅ Made created_date NOT NULL")
        
        # Make updated_date NOT NULL
        if 'updated_date' not in current_columns or current_columns['updated_date']['nullable'] == 'YES':
            await conn.execute(text("""
                ALTER TABLE production.manual_tasks 
                ALTER COLUMN updated_date SET NOT NULL;
            """))
            print("✅ Made updated_date NOT NULL")
        
        # Step 5: Optional - Drop old columns (commented out for safety)
        print("\n⚠️  Old columns that can be dropped after verification:")
        old_columns_to_drop = ['created_at', 'updated_at', 'status', 'processing_start_time', 'processing_end_time']
        
        for col in old_columns_to_drop:
            if col in current_columns:
                print(f"   - {col} (currently exists)")
                # Uncomment the following lines to actually drop the columns:
                # await conn.execute(text(f"ALTER TABLE production.manual_tasks DROP COLUMN {col};"))
                # print(f"✅ Dropped column: {col}")
        
        print("\n🎉 Migration completed successfully!")
        print("\n📝 Next steps:")
        print("1. Verify the data migration worked correctly")
        print("2. Test the application with the new structure")
        print("3. Uncomment the DROP COLUMN statements above to remove old columns")
        
        # Get final column count
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM production.manual_tasks;
        """))
        record_count = result.scalar()
        print(f"4. Total records in manual_tasks: {record_count}")


async def rollback_migration():
    """
    Rollback function to restore old column data if needed.
    """
    engine = get_supabase_async_engine()
    
    async with engine.begin() as conn:
        print("🔄 Rolling back migration...")
        
        # Restore old columns from new ones
        try:
            # Restore created_at from created_date
            await conn.execute(text("""
                UPDATE production.manual_tasks 
                SET created_at = created_date 
                WHERE created_at IS NULL AND created_date IS NOT NULL;
            """))
            
            # Restore updated_at from updated_date
            await conn.execute(text("""
                UPDATE production.manual_tasks 
                SET updated_at = updated_date 
                WHERE updated_at IS NULL AND updated_date IS NOT NULL;
            """))
            
            # Restore status from current_status
            await conn.execute(text("""
                UPDATE production.manual_tasks 
                SET status = current_status 
                WHERE status IS NULL AND current_status IS NOT NULL;
            """))
            
            print("✅ Rollback completed successfully!")
            
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback_migration())
    else:
        asyncio.run(migrate_manual_tasks_table())

#!/usr/bin/env python3
"""
Fast Bulk Update Task Mapping

This script uses efficient bulk SQL UPDATE statements to update existing records
with task mapping based on ref_id from test schema.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
import pandas as pd
from datetime import datetime

# Add src to path
sys.path.append('src')

# Load environment variables
load_dotenv()

def get_database_connection():
    """Create database connection."""
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    
    connection_string = f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require'
    return create_engine(connection_string)

def create_bulk_migration_task(engine, prod_schema='production'):
    """Create a bulk migration automation task for legacy data."""
    
    print("🔄 Creating bulk migration automation task...")
    
    insert_query = f"""
    INSERT INTO {prod_schema}.automation_tasks 
    (product_id, batch_id, current_status, error_message, processing_info, imputeop, created_date, updated_date)
    VALUES 
    (NULL, 'FAST_BULK_UPDATE_2025', 'completed', NULL, 
     '{{"migration_type": "fast_bulk_update", "migration_date": "{datetime.now().isoformat()}", "description": "Fast bulk update of existing records with task mapping"}}',
     '{{"migration_source": "test_schema", "migration_type": "fast_bulk_update"}}',
     NOW(), NOW())
    RETURNING id;
    """
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(insert_query))
            task_id = result.fetchone()[0]
            conn.commit()
            print(f"✅ Created bulk migration automation task with ID: {task_id}")
            return task_id
    except Exception as e:
        print(f"❌ Failed to create bulk migration task: {str(e)}")
        return None

def fast_bulk_update_table(engine, table_name, bulk_task_id, test_schema='test', prod_schema='production'):
    """Fast bulk update using SQL JOIN operations."""
    
    print(f"\n--- Fast bulk updating {table_name} ---")
    
    # Determine primary key column
    if table_name == 'document_media':
        pk_col = 'id'
    elif table_name == 'product_sellers':
        pk_col = 'seller_id'
    elif table_name == 'product_attributes':
        pk_col = 'id'
    elif table_name == 'product_extras':
        pk_col = 'extra_id'
    else:
        print(f"❌ Unknown table: {table_name}")
        return False
    
    # First, check what records exist in both schemas
    check_query = f"""
    SELECT 
        COUNT(*) as test_count,
        COUNT(p.{pk_col}) as prod_count,
        COUNT(CASE WHEN t.ref_id IS NULL OR t.ref_id = 0 THEN 1 END) as null_zero_ref_id,
        COUNT(CASE WHEN t.ref_id > 0 THEN 1 END) as valid_ref_id
    FROM {test_schema}.{table_name} t
    LEFT JOIN {prod_schema}.{table_name} p ON t.{pk_col} = p.{pk_col}
    """
    
    try:
        with engine.connect() as conn:
            result = pd.read_sql(check_query, conn)
            stats = result.iloc[0]
            
            print(f"📊 Analysis for {table_name}:")
            print(f"   Records in test: {stats['test_count']}")
            print(f"   Records in production: {stats['prod_count']}")
            print(f"   NULL/0 ref_id: {stats['null_zero_ref_id']}")
            print(f"   Valid ref_id: {stats['valid_ref_id']}")
            
            if stats['prod_count'] == 0:
                print(f"⚠️  No records to update in production.{table_name}")
                return True
            
            # Bulk update using JOIN - much faster than row-by-row
            bulk_update_query = f"""
            UPDATE {prod_schema}.{table_name} 
            SET 
                manual_task_id = NULL,
                automation_task_id = CASE 
                    WHEN t.ref_id IS NULL OR t.ref_id = 0 THEN {bulk_task_id}
                    ELSE t.ref_id
                END,
                updated_date = NOW()
            FROM {test_schema}.{table_name} t
            WHERE {prod_schema}.{table_name}.{pk_col} = t.{pk_col}
            """
            
            print(f"🚀 Executing bulk update...")
            result = conn.execute(text(bulk_update_query))
            updated_count = result.rowcount
            conn.commit()
            
            print(f"✅ Successfully updated {updated_count} records in {table_name}")
            return True
            
    except Exception as e:
        print(f"❌ Error updating {table_name}: {str(e)}")
        return False

def verify_task_mapping(engine, table_name, prod_schema='production'):
    """Verify that task mapping was applied correctly."""
    
    print(f"\n🔍 Verifying task mapping for {table_name}...")
    
    query = f"""
    SELECT 
        COUNT(*) as total_records,
        COUNT(manual_task_id) as has_manual_task,
        COUNT(automation_task_id) as has_automation_task,
        COUNT(CASE WHEN manual_task_id IS NULL AND automation_task_id IS NULL THEN 1 END) as no_task_mapping
    FROM {prod_schema}.{table_name}
    """
    
    try:
        result = pd.read_sql(query, engine)
        stats = result.iloc[0]
        
        print(f"   Total records: {stats['total_records']}")
        print(f"   With manual_task_id: {stats['has_manual_task']}")
        print(f"   With automation_task_id: {stats['has_automation_task']}")
        print(f"   Without task mapping: {stats['no_task_mapping']}")
        
        return stats['no_task_mapping'] == 0
        
    except Exception as e:
        print(f"❌ Error verifying {table_name}: {str(e)}")
        return False

def get_table_count(engine, schema, table):
    """Get count of records in table."""
    query = f"SELECT COUNT(*) as count FROM {schema}.{table}"
    try:
        result = pd.read_sql(query, engine)
        return result['count'].iloc[0]
    except Exception as e:
        print(f"Error counting records in {schema}.{table}: {str(e)}")
        return 0

def main():
    """Main update function."""
    
    print("=" * 80)
    print("FAST BULK UPDATE EXISTING RECORDS WITH TASK MAPPING")
    print("=" * 80)
    
    # Tables to update
    tables_to_update = [
        'document_media',
        'product_sellers',
        'product_attributes',
        'product_extras'
    ]
    
    try:
        # Create database connection
        engine = get_database_connection()
        print("✅ Database connection established")
        
        # Check schemas exist
        inspector = inspect(engine)
        schemas = inspector.get_schema_names()
        
        if 'test' not in schemas:
            print("❌ Test schema does not exist")
            return False
            
        if 'production' not in schemas:
            print("❌ Production schema does not exist")
            return False
        
        print("✅ Both test and production schemas exist")
        
        # Create bulk migration automation task
        bulk_task_id = create_bulk_migration_task(engine)
        if bulk_task_id is None:
            print("❌ Failed to create bulk migration task. Aborting.")
            return False
        
        # Fast bulk update each table
        update_results = {}
        
        print(f"\n🚀 FAST BULK UPDATE MODE: Using SQL JOIN operations")
        print("=" * 60)
        
        for table in tables_to_update:
            success = fast_bulk_update_table(engine, table, bulk_task_id)
            update_results[table] = success
        
        # Verify updates
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)
        
        for table in tables_to_update:
            if update_results[table]:
                verify_task_mapping(engine, table)
        
        # Summary
        print("\n" + "=" * 80)
        print("UPDATE SUMMARY")
        print("=" * 80)
        
        successful_updates = 0
        failed_updates = 0
        
        for table, success in update_results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            count = get_table_count(engine, 'production', table)
            print(f"{table:20} : {status} ({count} records in production)")
            if success:
                successful_updates += 1
            else:
                failed_updates += 1
        
        print(f"\nBulk Migration Task ID: {bulk_task_id}")
        print(f"Total: {successful_updates} successful, {failed_updates} failed")
        
        if failed_updates == 0:
            print("\n🎉 All table updates completed successfully!")
            print(f"📋 Records are now properly linked to automation task {bulk_task_id}")
            return True
        else:
            print(f"\n⚠️  {failed_updates} updates failed. Please check the errors above.")
            return False
            
    except Exception as e:
        print(f"❌ Update failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)

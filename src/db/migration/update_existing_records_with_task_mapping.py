#!/usr/bin/env python3
"""
Update Existing Records with Task Mapping

This script updates existing records in production tables to add the new
manual_task_id and automation_task_id foreign key mappings based on ref_id
from the test schema.
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
    
    # Create the automation task
    insert_query = f"""
    INSERT INTO {prod_schema}.automation_tasks 
    (product_id, batch_id, current_status, error_message, processing_info, imputeop, created_date, updated_date)
    VALUES 
    (NULL, 'BULK_MIGRATION_UPDATE_2025', 'completed', NULL, 
     '{{"migration_type": "bulk_legacy_update", "migration_date": "{datetime.now().isoformat()}", "description": "Bulk update of existing records with task mapping"}}',
     '{{"migration_source": "test_schema", "migration_type": "bulk_legacy_update"}}',
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

def update_table_with_task_mapping(engine, table_name, bulk_task_id, test_schema='test', prod_schema='production', limit_rows=None):
    """Update existing records with task mapping based on ref_id from test schema."""
    
    print(f"\n--- Updating {table_name} with task mapping ---")
    
    # Get ref_id mapping from test schema
    if limit_rows:
        test_query = f"SELECT * FROM {test_schema}.{table_name} LIMIT {limit_rows}"
        print(f"🔍 Testing with LIMIT {limit_rows} rows from {test_schema}.{table_name}")
    else:
        test_query = f"SELECT * FROM {test_schema}.{table_name}"
    
    try:
        test_df = pd.read_sql(test_query, engine)
        
        if test_df.empty:
            print(f"⚠️  No data in {test_schema}.{table_name}")
            return True
        
        if 'ref_id' not in test_df.columns:
            print(f"⚠️  No ref_id column in {test_schema}.{table_name}")
            return True
        
        # Analyze ref_id values
        ref_id_stats = {
            'total_records': len(test_df),
            'null_ref_id': len(test_df[test_df['ref_id'].isnull()]),
            'zero_ref_id': len(test_df[test_df['ref_id'] == 0]),
            'valid_ref_id': len(test_df[(test_df['ref_id'].notnull()) & (test_df['ref_id'] != 0)])
        }
        
        print(f"📊 ref_id analysis for {table_name} (processing {len(test_df)} rows):")
        print(f"   Total: {ref_id_stats['total_records']}")
        print(f"   NULL ref_id: {ref_id_stats['null_ref_id']}")
        print(f"   Zero ref_id: {ref_id_stats['zero_ref_id']}")
        print(f"   Valid ref_id: {ref_id_stats['valid_ref_id']}")
        
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
        
        # Update records in batches
        updated_count = 0
        failed_count = 0
        
        for _, row in test_df.iterrows():
            pk_value = row[pk_col]
            ref_id = row['ref_id']
            
            # Determine task mapping
            if pd.isna(ref_id) or ref_id == 0:
                manual_task_id = None
                automation_task_id = bulk_task_id
            else:
                manual_task_id = None
                automation_task_id = int(ref_id)
            
            # Update the production record
            update_query = f"""
            UPDATE {prod_schema}.{table_name} 
            SET manual_task_id = :manual_task_id, 
                automation_task_id = :automation_task_id, 
                updated_date = NOW()
            WHERE {pk_col} = :pk_value
            """
            
            params = {
                'manual_task_id': manual_task_id,
                'automation_task_id': automation_task_id,
                'pk_value': pk_value
            }
            
            try:
                with engine.connect() as conn:
                    result = conn.execute(text(update_query), params)
                    if result.rowcount > 0:
                        updated_count += 1
                    else:
                        print(f"⚠️  No record found with {pk_col}={pk_value}")
                        failed_count += 1
                    conn.commit()
            except Exception as e:
                print(f"❌ Failed to update {pk_col}={pk_value}: {str(e)}")
                failed_count += 1
        
        print(f"🔄 Update results for {table_name}:")
        print(f"   Successfully updated: {updated_count}")
        print(f"   Failed updates: {failed_count}")
        
        return failed_count == 0
        
    except Exception as e:
        print(f"❌ Error processing {table_name}: {str(e)}")
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

def verify_task_mapping(engine, table_name, prod_schema='production', limit_check=10):
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

def main():
    """Main update function."""
    
    print("=" * 80)
    print("UPDATE EXISTING RECORDS WITH TASK MAPPING")
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
        
        # Update each table (processing ALL records)
        update_results = {}
        
        print(f"\n🚀 PRODUCTION MODE: Processing ALL records")
        print("=" * 60)
        
        for table in tables_to_update:
            success = update_table_with_task_mapping(engine, table, bulk_task_id, limit_rows=None)
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

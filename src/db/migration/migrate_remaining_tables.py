#!/usr/bin/env python3
"""
Migrate Remaining Tables from Test Schema to Production Schema

This script migrates the remaining operational tables and handles ref_id mapping:
- products
- document_media
- product_sellers  
- product_attributes
- product_extras

For records with ref_id=0 or NULL, creates a bulk migration automation task.
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
    (NULL, 'BULK_MIGRATION_2025', 'completed', NULL, 
     '{{"migration_type": "bulk_legacy_data", "migration_date": "{datetime.now().isoformat()}", "description": "Bulk migration of legacy data from test schema"}}',
     '{{"migration_source": "test_schema", "migration_type": "bulk_legacy_data"}}',
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

def get_table_data_with_ref_mapping(engine, schema, table, limit_rows=None):
    """Get table data and analyze ref_id values."""
    if limit_rows:
        query = f"SELECT * FROM {schema}.{table} LIMIT {limit_rows}"
        print(f"🔍 Testing with LIMIT {limit_rows} rows from {schema}.{table}")
    else:
        query = f"SELECT * FROM {schema}.{table}"
    
    try:
        df = pd.read_sql(query, engine)
        
        # Analyze ref_id values
        if 'ref_id' in df.columns:
            ref_id_stats = {
                'total_records': len(df),
                'null_ref_id': len(df[df['ref_id'].isnull()]),
                'zero_ref_id': len(df[df['ref_id'] == 0]),
                'valid_ref_id': len(df[(df['ref_id'].notnull()) & (df['ref_id'] != 0)])
            }
            print(f"📊 ref_id analysis for {table} (limited to {len(df)} rows):")
            print(f"   Total: {ref_id_stats['total_records']}")
            print(f"   NULL ref_id: {ref_id_stats['null_ref_id']}")
            print(f"   Zero ref_id: {ref_id_stats['zero_ref_id']}")
            print(f"   Valid ref_id: {ref_id_stats['valid_ref_id']}")
            
            return df, ref_id_stats
        else:
            return df, {'total_records': len(df), 'no_ref_id_column': True}
            
    except Exception as e:
        print(f"Error reading from {schema}.{table}: {str(e)}")
        return None, None

def transform_data_for_production(df, table_name, bulk_task_id):
    """Transform test schema data for production schema with new foreign key design."""
    
    if df is None or df.empty:
        return df
    
    # Create a copy to avoid modifying original
    df_prod = df.copy()
    
    # Handle ref_id mapping based on table
    if 'ref_id' in df_prod.columns:
        # Create new foreign key columns
        df_prod['manual_task_id'] = None
        df_prod['automation_task_id'] = None
        
        # Map ref_id values:
        # - ref_id = 0 or NULL -> automation_task_id = bulk_task_id
        # - ref_id > 0 -> automation_task_id = ref_id (assuming they're automation tasks)
        
        # For NULL or 0 ref_id, assign to bulk migration task
        null_or_zero_mask = (df_prod['ref_id'].isnull()) | (df_prod['ref_id'] == 0)
        df_prod.loc[null_or_zero_mask, 'automation_task_id'] = bulk_task_id
        
        # For valid ref_id > 0, assume they're automation task IDs
        valid_ref_mask = (df_prod['ref_id'].notnull()) & (df_prod['ref_id'] > 0)
        df_prod.loc[valid_ref_mask, 'automation_task_id'] = df_prod.loc[valid_ref_mask, 'ref_id']
        
        # Remove the old ref_id column
        df_prod = df_prod.drop('ref_id', axis=1)
        
        print(f"🔄 Transformed {table_name}:")
        print(f"   Records assigned to bulk task: {null_or_zero_mask.sum()}")
        print(f"   Records with existing task IDs: {valid_ref_mask.sum()}")
    
    return df_prod

def migrate_table_with_ref_mapping(engine, table_name, bulk_task_id, test_schema='test', prod_schema='production', limit_rows=None):
    """Migrate table data with proper ref_id to foreign key mapping."""
    
    print(f"\n--- Migrating {table_name} with ref_id mapping ---")
    
    # Check if tables exist
    inspector = inspect(engine)
    test_tables = inspector.get_table_names(schema=test_schema)
    prod_tables = inspector.get_table_names(schema=prod_schema)
    
    if table_name not in test_tables:
        print(f"❌ Table {test_schema}.{table_name} does not exist")
        return False
    
    if table_name not in prod_tables:
        print(f"❌ Table {prod_schema}.{table_name} does not exist")
        return False
    
    # Get data with ref_id analysis (with optional row limit for testing)
    df, ref_stats = get_table_data_with_ref_mapping(engine, test_schema, table_name, limit_rows)
    
    if df is None:
        print(f"❌ Failed to read data from {test_schema}.{table_name}")
        return False
    
    if df.empty:
        print(f"⚠️  No data to migrate from {test_schema}.{table_name}")
        return True
    
    # Transform data for production schema
    df_prod = transform_data_for_production(df, table_name, bulk_task_id)
    
    # Insert data to production schema
    print(f"📤 Inserting {len(df_prod)} records to {prod_schema}.{table_name}...")
    
    try:
        df_prod.to_sql(table_name, engine, schema=prod_schema, if_exists='append', index=False, method='multi')
        print(f"✅ Successfully migrated {len(df_prod)} records")
        return True
    except Exception as e:
        print(f"❌ Failed to insert data to {prod_schema}.{table_name}: {str(e)}")
        print(f"🔍 Error details: {type(e).__name__}")
        # Print more detailed error information
        if hasattr(e, 'orig'):
            print(f"🔍 Original error: {e.orig}")
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
    """Main migration function."""
    
    print("=" * 80)
    print("REMAINING TABLES MIGRATION: TEST SCHEMA → PRODUCTION SCHEMA")
    print("=" * 80)
    
    # Tables to migrate (in dependency order)
    # Note: products table is already migrated, only migrate tables with ref_id
    tables_to_migrate = [
        'document_media',     # Depends on products
        'product_sellers',    # Depends on products
        'product_attributes', # Depends on products and attributes
        'product_extras'      # Depends on products
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
        
        # Migrate each table (with 5 row limit for testing)
        migration_results = {}
        TEST_LIMIT = 5  # Limit to 5 rows per table for testing
        
        print(f"\n🧪 TESTING MODE: Processing only {TEST_LIMIT} rows per table")
        print("=" * 60)
        
        for table in tables_to_migrate:
            success = migrate_table_with_ref_mapping(engine, table, bulk_task_id, limit_rows=TEST_LIMIT)
            migration_results[table] = success
        
        # Summary
        print("\n" + "=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        
        successful_migrations = 0
        failed_migrations = 0
        
        for table, success in migration_results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            count = get_table_count(engine, 'production', table)
            print(f"{table:20} : {status} ({count} records in production)")
            if success:
                successful_migrations += 1
            else:
                failed_migrations += 1
        
        print(f"\nBulk Migration Task ID: {bulk_task_id}")
        print(f"Total: {successful_migrations} successful, {failed_migrations} failed")
        
        if failed_migrations == 0:
            print("\n🎉 All remaining table migrations completed successfully!")
            print(f"📋 Records with ref_id=0 or NULL are now linked to automation task {bulk_task_id}")
            return True
        else:
            print(f"\n⚠️  {failed_migrations} migrations failed. Please check the errors above.")
            return False
            
    except Exception as e:
        print(f"❌ Migration failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)

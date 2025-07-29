#!/usr/bin/env python3
"""
Migrate All Remaining Records from Test to Production

This script migrates ALL remaining records from test schema to production schema
for the tables: document_media, product_sellers, product_attributes, product_extras
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
    (NULL, 'COMPLETE_MIGRATION_2025', 'completed', NULL, 
     '{{"migration_type": "complete_migration", "migration_date": "{datetime.now().isoformat()}", "description": "Complete migration of all remaining records from test to production"}}',
     '{{"migration_source": "test_schema", "migration_type": "complete_migration"}}',
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

def migrate_all_records_for_table(engine, table_name, bulk_task_id, test_schema='test', prod_schema='production'):
    """Migrate all records from test to production for a specific table."""
    
    print(f"\n--- Migrating ALL records for {table_name} ---")
    
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
    
    try:
        with engine.connect() as conn:
            # First, get statistics
            stats_query = f"""
            SELECT 
                COUNT(*) as test_count,
                (SELECT COUNT(*) FROM {prod_schema}.{table_name}) as prod_count
            FROM {test_schema}.{table_name}
            """
            
            stats_result = pd.read_sql(stats_query, conn)
            test_count = stats_result.iloc[0]['test_count']
            prod_count = stats_result.iloc[0]['prod_count']
            
            print(f"📊 Current status:")
            print(f"   Test records: {test_count}")
            print(f"   Production records: {prod_count}")
            print(f"   Records to migrate: {test_count - prod_count}")
            
            if test_count == 0:
                print(f"⚠️  No records in test.{table_name}")
                return True
            
            if test_count == prod_count:
                print(f"✅ All records already migrated for {table_name}")
                return True
            
            # Use INSERT ... SELECT with ON CONFLICT to handle duplicates
            # Transform ref_id to task mapping during insert
            if table_name == 'product_sellers':
                # product_sellers has TEXT primary key
                insert_query = f"""
                INSERT INTO {prod_schema}.{table_name} 
                (seller_id, product_id, seller_name, seller_type, created_date, updated_date, source, 
                 manual_task_id, automation_task_id, notes, source_url)
                SELECT 
                    t.seller_id,
                    t.product_id,
                    t.seller_name,
                    t.seller_type,
                    t.created_date,
                    t.updated_date,
                    t.source,
                    NULL as manual_task_id,
                    CASE 
                        WHEN t.ref_id IS NULL OR t.ref_id = 0 THEN {bulk_task_id}
                        ELSE t.ref_id
                    END as automation_task_id,
                    NULL as notes,
                    NULL as source_url
                FROM {test_schema}.{table_name} t
                ON CONFLICT (seller_id) DO UPDATE SET
                    manual_task_id = NULL,
                    automation_task_id = CASE 
                        WHEN EXCLUDED.automation_task_id IS NOT NULL THEN EXCLUDED.automation_task_id
                        ELSE {bulk_task_id}
                    END,
                    updated_date = NOW()
                """
            else:
                # Other tables have numeric primary keys - need explicit column mapping
                if table_name == 'document_media':
                    insert_query = f"""
                    INSERT INTO {prod_schema}.{table_name} 
                    (id, product_id, url, created_date, updated_date, type, description, source, 
                     manual_task_id, automation_task_id, notes, source_url)
                    SELECT 
                        t.id, t.product_id, t.url, t.created_date, t.updated_date, t.type, t.description, t.source,
                        NULL as manual_task_id,
                        {bulk_task_id} as automation_task_id,
                        NULL as notes,
                        NULL as source_url
                    FROM {test_schema}.{table_name} t
                    WHERE t.{pk_col} NOT IN (SELECT {pk_col} FROM {prod_schema}.{table_name})
                    """
                elif table_name == 'product_attributes':
                    insert_query = f"""
                    INSERT INTO {prod_schema}.{table_name} 
                    (id, product_id, attribute_id, value_text, value_float, value_unit, created_date, updated_date, source,
                     manual_task_id, automation_task_id, notes, source_url)
                    SELECT 
                        t.id, t.product_id, t.attribute_id, t.value_text, t.value_float, t.value_unit, 
                        t.created_date, t.updated_date, t.source,
                        NULL as manual_task_id,
                        {bulk_task_id} as automation_task_id,
                        NULL as notes,
                        NULL as source_url
                    FROM {test_schema}.{table_name} t
                    WHERE t.{pk_col} NOT IN (SELECT {pk_col} FROM {prod_schema}.{table_name})
                    """
                elif table_name == 'product_extras':
                    insert_query = f"""
                    INSERT INTO {prod_schema}.{table_name} 
                    (extra_id, product_id, name, value, created_date, updated_date, source,
                     manual_task_id, automation_task_id, notes, source_url)
                    SELECT 
                        t.extra_id, t.product_id, t.name, t.value, t.created_date, t.updated_date, t.source,
                        NULL as manual_task_id,
                        {bulk_task_id} as automation_task_id,
                        NULL as notes,
                        NULL as source_url
                    FROM {test_schema}.{table_name} t
                    WHERE t.{pk_col} NOT IN (SELECT {pk_col} FROM {prod_schema}.{table_name})
                    """
                else:
                    print(f"❌ No column mapping defined for {table_name}")
                    return False
            
            print(f"🚀 Executing bulk insert...")
            result = conn.execute(text(insert_query))
            inserted_count = result.rowcount
            conn.commit()
            
            print(f"✅ Successfully migrated {inserted_count} new records to {table_name}")
            
            # Verify final count
            final_count_query = f"SELECT COUNT(*) as count FROM {prod_schema}.{table_name}"
            final_result = pd.read_sql(final_count_query, conn)
            final_count = final_result.iloc[0]['count']
            
            print(f"📊 Final production count: {final_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error migrating {table_name}: {str(e)}")
        return False

def verify_migration_completion(engine, table_name, test_schema='test', prod_schema='production'):
    """Verify that migration is complete."""
    
    print(f"\n🔍 Verifying migration completion for {table_name}...")
    
    try:
        with engine.connect() as conn:
            # Compare counts
            comparison_query = f"""
            SELECT 
                (SELECT COUNT(*) FROM {test_schema}.{table_name}) as test_count,
                (SELECT COUNT(*) FROM {prod_schema}.{table_name}) as prod_count
            """
            
            result = pd.read_sql(comparison_query, conn)
            test_count = result.iloc[0]['test_count']
            prod_count = result.iloc[0]['prod_count']
            
            print(f"   Test records: {test_count}")
            print(f"   Production records: {prod_count}")
            
            if test_count == prod_count:
                print(f"   ✅ Migration complete - counts match")
                return True
            else:
                print(f"   ❌ Migration incomplete - {test_count - prod_count} records missing")
                return False
                
    except Exception as e:
        print(f"❌ Error verifying {table_name}: {str(e)}")
        return False

def main():
    """Main migration function."""
    
    print("=" * 80)
    print("MIGRATE ALL REMAINING RECORDS: TEST SCHEMA → PRODUCTION SCHEMA")
    print("=" * 80)
    
    # Tables to migrate completely
    tables_to_migrate = [
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
        
        # Migrate all records for each table
        migration_results = {}
        
        print(f"\n🚀 COMPLETE MIGRATION MODE: Migrating ALL records")
        print("=" * 60)
        
        for table in tables_to_migrate:
            success = migrate_all_records_for_table(engine, table, bulk_task_id)
            migration_results[table] = success
        
        # Verify migrations
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)
        
        verification_results = {}
        for table in tables_to_migrate:
            if migration_results[table]:
                verification_results[table] = verify_migration_completion(engine, table)
            else:
                verification_results[table] = False
        
        # Summary
        print("\n" + "=" * 80)
        print("COMPLETE MIGRATION SUMMARY")
        print("=" * 80)
        
        successful_migrations = 0
        failed_migrations = 0
        
        for table in tables_to_migrate:
            migration_success = migration_results[table]
            verification_success = verification_results.get(table, False)
            overall_success = migration_success and verification_success
            
            status = "✅ SUCCESS" if overall_success else "❌ FAILED"
            
            # Get final counts
            try:
                with engine.connect() as conn:
                    count_query = f"SELECT COUNT(*) as count FROM production.{table}"
                    count_result = pd.read_sql(count_query, conn)
                    final_count = count_result.iloc[0]['count']
            except:
                final_count = "ERROR"
            
            print(f"{table:20} : {status} ({final_count} records in production)")
            
            if overall_success:
                successful_migrations += 1
            else:
                failed_migrations += 1
        
        print(f"\nBulk Migration Task ID: {bulk_task_id}")
        print(f"Total: {successful_migrations} successful, {failed_migrations} failed")
        
        if failed_migrations == 0:
            print("\n🎉 Complete migration finished successfully!")
            print(f"📋 All records migrated and linked to automation task {bulk_task_id}")
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

#!/usr/bin/env python3
"""
Migrate Data from Test Schema to Production Schema

This script migrates data from test schema to production schema for:
- categories
- attributes  
- manufacturers
- category_attributes
- part_numbers
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
import pandas as pd

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

def check_table_exists(engine, schema, table):
    """Check if table exists in schema."""
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema=schema)
    return table in tables

def get_table_data(engine, schema, table):
    """Get all data from a table."""
    query = f"SELECT * FROM {schema}.{table}"
    try:
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print(f"Error reading from {schema}.{table}: {str(e)}")
        return None

def insert_data_to_table(engine, schema, table, df):
    """Insert data into table."""
    try:
        # Use pandas to_sql with if_exists='append' to add data
        df.to_sql(table, engine, schema=schema, if_exists='append', index=False, method='multi')
        return True
    except Exception as e:
        print(f"Error inserting data to {schema}.{table}: {str(e)}")
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

def migrate_table_data(engine, table_name, test_schema='test', prod_schema='production'):
    """Migrate data from test schema to production schema for a specific table."""
    
    print(f"\n--- Migrating {table_name} ---")
    
    # Check if tables exist
    if not check_table_exists(engine, test_schema, table_name):
        print(f"❌ Table {test_schema}.{table_name} does not exist")
        return False
    
    if not check_table_exists(engine, prod_schema, table_name):
        print(f"❌ Table {prod_schema}.{table_name} does not exist")
        return False
    
    # Get counts before migration
    test_count = get_table_count(engine, test_schema, table_name)
    prod_count_before = get_table_count(engine, prod_schema, table_name)
    
    print(f"📊 {test_schema}.{table_name}: {test_count} records")
    print(f"📊 {prod_schema}.{table_name}: {prod_count_before} records (before migration)")
    
    if test_count == 0:
        print(f"⚠️  No data to migrate from {test_schema}.{table_name}")
        return True
    
    # Get data from test schema
    print(f"📥 Reading data from {test_schema}.{table_name}...")
    df = get_table_data(engine, test_schema, table_name)
    
    if df is None or df.empty:
        print(f"❌ Failed to read data from {test_schema}.{table_name}")
        return False
    
    print(f"✅ Read {len(df)} records from {test_schema}.{table_name}")
    
    # Insert data to production schema
    print(f"📤 Inserting data to {prod_schema}.{table_name}...")
    success = insert_data_to_table(engine, prod_schema, table_name, df)
    
    if not success:
        print(f"❌ Failed to insert data to {prod_schema}.{table_name}")
        return False
    
    # Verify migration
    prod_count_after = get_table_count(engine, prod_schema, table_name)
    migrated_count = prod_count_after - prod_count_before
    
    print(f"✅ Successfully migrated {migrated_count} records")
    print(f"📊 {prod_schema}.{table_name}: {prod_count_after} records (after migration)")
    
    return True

def main():
    """Main migration function."""
    
    print("=" * 70)
    print("DATA MIGRATION: TEST SCHEMA → PRODUCTION SCHEMA")
    print("=" * 70)
    
    # Tables to migrate (in dependency order)
    tables_to_migrate = [
        'manufacturers',    # No dependencies
        'categories',       # No dependencies  
        'attributes',       # No dependencies
        'part_numbers',     # May depend on manufacturers
        'category_attributes'  # Depends on categories and attributes
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
        
        # Migrate each table
        migration_results = {}
        
        for table in tables_to_migrate:
            success = migrate_table_data(engine, table)
            migration_results[table] = success
        
        # Summary
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        
        successful_migrations = 0
        failed_migrations = 0
        
        for table, success in migration_results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{table:20} : {status}")
            if success:
                successful_migrations += 1
            else:
                failed_migrations += 1
        
        print(f"\nTotal: {successful_migrations} successful, {failed_migrations} failed")
        
        if failed_migrations == 0:
            print("\n🎉 All data migrations completed successfully!")
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

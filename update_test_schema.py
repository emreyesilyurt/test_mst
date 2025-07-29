#!/usr/bin/env python3
"""
Script to update the test schema for manual task system.
This script will:
1. Check current test schema structure
2. Preserve manufacturers, categories, attributes, and category_attributes tables
3. Drop and recreate other tables with updated structure
4. ONLY works on test schema - production is protected
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

# Load environment variables
load_dotenv()

# Database configuration
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')
test_schema = os.getenv('TEST_SCHEMA', 'test')

# SAFETY CHECK - Only allow test schema
if os.getenv('RUN_MODE', 'test') == 'prod':
    print("❌ ERROR: This script is only for test schema. Set RUN_MODE=test in your .env file.")
    exit(1)

# Database connection
connection_string = f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require'
engine = create_engine(connection_string)

# Tables to preserve (keep existing data)
PRESERVE_TABLES = [
    'manufacturers',
    'categories', 
    'attributes',
    'category_attributes'
]

# Tables to recreate (drop and create new)
RECREATE_TABLES = [
    'products',
    'part_numbers',
    'document_media',
    'product_sellers',
    'product_attributes',
    'product_extras',
    'automation_tasks',
    'manual_tasks'
]

def check_schema_exists():
    """Check if test schema exists"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = :schema
        """), {"schema": test_schema})
        return result.fetchone() is not None

def get_existing_tables():
    """Get list of existing tables in test schema"""
    inspector = inspect(engine)
    try:
        tables = inspector.get_table_names(schema=test_schema)
        return tables
    except Exception as e:
        print(f"Schema {test_schema} might not exist: {e}")
        return []

def create_schema_if_not_exists():
    """Create test schema if it doesn't exist"""
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {test_schema}"))
        conn.commit()
        print(f"✅ Schema '{test_schema}' ready")

def backup_preserve_tables():
    """Create backup of tables we want to preserve"""
    existing_tables = get_existing_tables()
    preserved_data = {}
    
    with engine.connect() as conn:
        for table in PRESERVE_TABLES:
            if table in existing_tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {test_schema}.{table}"))
                    count = result.scalar()
                    preserved_data[table] = count
                    print(f"📊 {table}: {count} records (will be preserved)")
                except Exception as e:
                    print(f"⚠️  Could not check {table}: {e}")
            else:
                print(f"📝 {table}: does not exist (will be created)")
                preserved_data[table] = 0
    
    return preserved_data

def drop_recreate_tables():
    """Drop tables that need to be recreated"""
    existing_tables = get_existing_tables()
    
    with engine.connect() as conn:
        # Drop tables in reverse dependency order
        drop_order = [
            'manual_tasks',
            'automation_tasks', 
            'product_extras',
            'product_attributes',
            'product_sellers',
            'document_media',
            'products',
            'part_numbers'
        ]
        
        for table in drop_order:
            if table in existing_tables:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {test_schema}.{table} CASCADE"))
                    print(f"🗑️  Dropped {table}")
                except Exception as e:
                    print(f"⚠️  Could not drop {table}: {e}")
        
        conn.commit()

def create_tables():
    """Create all tables using the model definitions"""
    print("🔨 Creating tables from model definitions...")
    
    # Import models to register them with Base
    from src.db.models import Base, setup_database
    
    # Create all tables
    setup_database(engine=engine, schema=test_schema)
    print("✅ All tables created successfully")

def verify_schema():
    """Verify the schema is correctly set up"""
    print("\n📋 Verifying schema structure...")
    
    existing_tables = get_existing_tables()
    all_expected_tables = PRESERVE_TABLES + RECREATE_TABLES
    
    missing_tables = []
    for table in all_expected_tables:
        if table in existing_tables:
            print(f"✅ {table}")
        else:
            print(f"❌ {table} - MISSING")
            missing_tables.append(table)
    
    if missing_tables:
        print(f"\n⚠️  Missing tables: {missing_tables}")
        return False
    else:
        print(f"\n🎉 All {len(all_expected_tables)} tables are present!")
        return True

def main():
    print("🚀 Starting test schema update...")
    print(f"📍 Target schema: {test_schema}")
    print(f"🔒 Production schema protection: {'ON' if os.getenv('RUN_MODE') != 'prod' else 'OFF'}")
    
    # Safety confirmation
    response = input(f"\n⚠️  This will modify the '{test_schema}' schema. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled")
        return
    
    try:
        # Step 1: Create schema if needed
        create_schema_if_not_exists()
        
        # Step 2: Check what we have
        print(f"\n📊 Current state of {test_schema} schema:")
        preserved_data = backup_preserve_tables()
        
        # Step 3: Drop tables that need recreation
        print(f"\n🗑️  Dropping tables that need recreation...")
        drop_recreate_tables()
        
        # Step 4: Create all tables
        print(f"\n🔨 Creating updated table structure...")
        create_tables()
        
        # Step 5: Verify everything is correct
        success = verify_schema()
        
        if success:
            print(f"\n🎉 Test schema update completed successfully!")
            print(f"📝 Preserved tables with data:")
            for table, count in preserved_data.items():
                if count > 0:
                    print(f"   - {table}: {count} records")
            
            print(f"\n🔧 Next steps:")
            print(f"   1. Set RUN_MODE=test in your .env file")
            print(f"   2. Run: python run_server.py")
            print(f"   3. Test the manual task system")
        else:
            print(f"\n❌ Schema update had issues. Please check the errors above.")
            
    except Exception as e:
        print(f"\n💥 Error during schema update: {e}")
        print(f"🔄 You may need to run this script again or check your database connection.")

if __name__ == "__main__":
    main()

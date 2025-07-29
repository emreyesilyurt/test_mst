#!/usr/bin/env python3
"""
Production Database Initialization Script

This script initializes all database tables in the production schema.
It creates the schema if it doesn't exist and then creates all tables
defined in the models.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

# Add src to path to import our modules
sys.path.append('src')

# Load environment variables
load_dotenv()

def create_production_schema():
    """Create the production schema if it doesn't exist."""
    
    # Database configuration
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    prod_schema = os.getenv('PROD_SCHEMA', 'production')
    
    # Create connection string
    connection_string = f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require'
    
    try:
        # Create engine
        engine = create_engine(connection_string)
        
        # Create schema if it doesn't exist
        with engine.connect() as conn:
            # Check if schema exists
            inspector = inspect(engine)
            schemas = inspector.get_schema_names()
            
            if prod_schema not in schemas:
                print(f"Creating schema '{prod_schema}'...")
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {prod_schema}"))
                conn.commit()
                print(f"Schema '{prod_schema}' created successfully.")
            else:
                print(f"Schema '{prod_schema}' already exists.")
        
        return engine, prod_schema
        
    except Exception as e:
        print(f"Error creating schema: {str(e)}")
        raise

def initialize_production_tables():
    """Initialize all tables in the production schema."""
    
    try:
        # Set environment to production mode
        os.environ['RUN_MODE'] = 'prod'
        
        # Create schema first
        engine, schema = create_production_schema()
        
        # Import models after setting RUN_MODE to prod
        from db.models import Base, setup_database, tables
        
        print(f"Initializing tables in schema '{schema}'...")
        print("Tables to be created:")
        for table_name, full_table_name in tables.items():
            print(f"  - {full_table_name}")
        
        # Create all tables
        setup_database(engine=engine, schema=schema)
        
        # Verify tables were created
        inspector = inspect(engine)
        created_tables = inspector.get_table_names(schema=schema)
        
        print(f"\nSuccessfully created {len(created_tables)} tables in schema '{schema}':")
        for table in sorted(created_tables):
            print(f"  ✓ {schema}.{table}")
        
        print(f"\nProduction database initialization completed successfully!")
        
    except Exception as e:
        print(f"Error initializing production tables: {str(e)}")
        print("\nPlease check:")
        print("1. Database connection parameters in .env file")
        print("2. Database server is accessible")
        print("3. User has necessary permissions to create schemas and tables")
        raise

def verify_production_setup():
    """Verify that all expected tables exist in production schema."""
    
    try:
        # Set environment to production mode
        os.environ['RUN_MODE'] = 'prod'
        
        # Import after setting RUN_MODE
        from db.models import engine, schema, tables
        
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names(schema=schema)
        
        print(f"\nVerifying production setup in schema '{schema}':")
        
        expected_tables = [name.split('.')[-1] for name in tables.values()]
        missing_tables = []
        
        for table in expected_tables:
            if table in existing_tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} (MISSING)")
                missing_tables.append(table)
        
        if missing_tables:
            print(f"\nWarning: {len(missing_tables)} tables are missing!")
            return False
        else:
            print(f"\nAll {len(expected_tables)} tables are present in production schema.")
            return True
            
    except Exception as e:
        print(f"Error verifying production setup: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("PRODUCTION DATABASE INITIALIZATION")
    print("=" * 60)
    
    # Check current environment settings
    print(f"Current RUN_MODE: {os.getenv('RUN_MODE', 'not set')}")
    print(f"Production Schema: {os.getenv('PROD_SCHEMA', 'production')}")
    print(f"Database Host: {os.getenv('DB_HOST', 'not set')}")
    print(f"Database Name: {os.getenv('DB_NAME', 'not set')}")
    print()
    
    try:
        # Initialize production tables
        initialize_production_tables()
        
        # Verify setup
        print("\n" + "=" * 60)
        verify_production_setup()
        print("=" * 60)
        
    except Exception as e:
        print(f"\nFailed to initialize production database: {str(e)}")
        sys.exit(1)

#!/usr/bin/env python3
"""
Drop all tables in production schema

This script drops all tables in the production schema so we can recreate them
with the correct foreign key relationships.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

# Add src to path
sys.path.append('src')

# Load environment variables
load_dotenv()

def drop_production_tables():
    """Drop all tables in the production schema."""
    
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
        
        # Get existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names(schema=prod_schema)
        
        if not existing_tables:
            print(f"No tables found in schema '{prod_schema}'")
            return
        
        print(f"Found {len(existing_tables)} tables in schema '{prod_schema}':")
        for table in existing_tables:
            print(f"  - {table}")
        
        # Drop all tables
        with engine.connect() as conn:
            print(f"\nDropping all tables in schema '{prod_schema}'...")
            
            # Drop tables in reverse order to handle foreign key constraints
            for table in reversed(existing_tables):
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {prod_schema}.{table} CASCADE"))
                    print(f"  ✓ Dropped {prod_schema}.{table}")
                except Exception as e:
                    print(f"  ✗ Failed to drop {prod_schema}.{table}: {str(e)}")
            
            conn.commit()
        
        # Verify tables are dropped
        inspector = inspect(engine)
        remaining_tables = inspector.get_table_names(schema=prod_schema)
        
        if remaining_tables:
            print(f"\nWarning: {len(remaining_tables)} tables still exist:")
            for table in remaining_tables:
                print(f"  - {table}")
        else:
            print(f"\nAll tables successfully dropped from schema '{prod_schema}'")
        
    except Exception as e:
        print(f"Error dropping tables: {str(e)}")
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("DROP PRODUCTION TABLES")
    print("=" * 60)
    
    try:
        drop_production_tables()
        print("=" * 60)
        print("Tables dropped successfully!")
        print("You can now run setup_production.py to recreate them with correct foreign keys.")
        
    except Exception as e:
        print(f"\nFailed to drop production tables: {str(e)}")
        sys.exit(1)

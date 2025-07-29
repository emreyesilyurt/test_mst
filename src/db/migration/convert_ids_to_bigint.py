#!/usr/bin/env python3
"""
Convert ID columns from INTEGER to BIGINT for scalability

This script converts all ID columns in both test and production schemas
from INTEGER to BIGINT to support millions of rows.
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

def get_id_columns_to_convert():
    """Define which ID columns need to be converted to BIGINT."""
    
    # Define tables and their ID columns that should be BIGINT
    schema_tables = {
        'test': {
            'products': ['product_id', 'manufacturer_id'],
            'document_media': ['id', 'product_id', 'ref_id'],
            'product_sellers': ['product_id', 'ref_id'],  # seller_id is TEXT, skip it
            'product_attributes': ['id', 'product_id', 'attribute_id', 'ref_id'],
            'product_extras': ['extra_id', 'product_id', 'ref_id']
        },
        'production': {
            'products': ['product_id', 'manufacturer_id'],
            'document_media': ['id', 'product_id', 'manual_task_id', 'automation_task_id'],
            'product_sellers': ['product_id', 'manual_task_id', 'automation_task_id'],
            'product_attributes': ['id', 'product_id', 'attribute_id', 'manual_task_id', 'automation_task_id'],
            'product_extras': ['extra_id', 'product_id', 'manual_task_id', 'automation_task_id'],
            'automation_tasks': ['id', 'product_id'],
            'manual_tasks': ['id', 'part_number_id']
        }
    }
    
    return schema_tables

def convert_column_to_bigint(engine, schema, table, column):
    """Convert a single column from INTEGER to BIGINT."""
    
    print(f"🔄 Converting {schema}.{table}.{column} to BIGINT...")
    
    try:
        with engine.connect() as conn:
            # PostgreSQL allows direct ALTER COLUMN for INTEGER to BIGINT conversion
            alter_query = f"""
            ALTER TABLE {schema}.{table} 
            ALTER COLUMN {column} TYPE BIGINT;
            """
            
            conn.execute(text(alter_query))
            conn.commit()
            print(f"✅ Successfully converted {schema}.{table}.{column} to BIGINT")
            return True
            
    except Exception as e:
        print(f"❌ Failed to convert {schema}.{table}.{column}: {str(e)}")
        return False

def verify_column_type(engine, schema, table, column):
    """Verify that a column is now BIGINT."""
    
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table, schema=schema)
        
        for col in columns:
            if col['name'] == column:
                col_type = str(col['type']).upper()
                if 'BIGINT' in col_type:
                    return True
                else:
                    print(f"⚠️  {schema}.{table}.{column} is still {col_type}")
                    return False
        
        print(f"❌ Column {column} not found in {schema}.{table}")
        return False
        
    except Exception as e:
        print(f"❌ Error verifying {schema}.{table}.{column}: {str(e)}")
        return False

def main():
    """Main conversion function."""
    
    print("=" * 80)
    print("CONVERTING ID COLUMNS FROM INTEGER TO BIGINT")
    print("=" * 80)
    
    try:
        # Create database connection
        engine = get_database_connection()
        print("✅ Database connection established")
        
        # Get tables and columns to convert
        schema_tables = get_id_columns_to_convert()
        
        conversion_results = {}
        total_conversions = 0
        successful_conversions = 0
        
        # Convert each column
        for schema, tables in schema_tables.items():
            print(f"\n--- Converting {schema.upper()} schema ---")
            
            for table, columns in tables.items():
                print(f"\n🔧 Processing {schema}.{table}")
                
                # Check if table exists
                inspector = inspect(engine)
                try:
                    table_columns = inspector.get_columns(table, schema=schema)
                    table_exists = True
                except:
                    print(f"⚠️  Table {schema}.{table} does not exist, skipping...")
                    continue
                
                for column in columns:
                    total_conversions += 1
                    
                    # Check if column exists and is INTEGER
                    column_exists = False
                    is_integer = False
                    
                    for col in table_columns:
                        if col['name'] == column:
                            column_exists = True
                            col_type = str(col['type']).upper()
                            if 'INTEGER' in col_type and 'BIGINT' not in col_type:
                                is_integer = True
                            elif 'BIGINT' in col_type:
                                print(f"ℹ️  {schema}.{table}.{column} is already BIGINT")
                                successful_conversions += 1
                                continue
                            break
                    
                    if not column_exists:
                        print(f"⚠️  Column {column} does not exist in {schema}.{table}, skipping...")
                        continue
                    
                    if not is_integer:
                        print(f"ℹ️  {schema}.{table}.{column} is not INTEGER type, skipping...")
                        continue
                    
                    # Convert the column
                    success = convert_column_to_bigint(engine, schema, table, column)
                    
                    if success:
                        # Verify the conversion
                        if verify_column_type(engine, schema, table, column):
                            successful_conversions += 1
                        else:
                            success = False
                    
                    conversion_results[f"{schema}.{table}.{column}"] = success
        
        # Summary
        print("\n" + "=" * 80)
        print("CONVERSION SUMMARY")
        print("=" * 80)
        
        failed_conversions = total_conversions - successful_conversions
        
        print(f"Total columns processed: {total_conversions}")
        print(f"Successful conversions: {successful_conversions}")
        print(f"Failed conversions: {failed_conversions}")
        
        if failed_conversions > 0:
            print(f"\n❌ Failed conversions:")
            for key, success in conversion_results.items():
                if not success:
                    print(f"   {key}")
        
        if failed_conversions == 0:
            print("\n🎉 All ID columns successfully converted to BIGINT!")
            print("📋 Your database is now ready to handle millions of rows.")
            return True
        else:
            print(f"\n⚠️  {failed_conversions} conversions failed. Please check the errors above.")
            return False
            
    except Exception as e:
        print(f"❌ Conversion failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)

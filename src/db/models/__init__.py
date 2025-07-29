"""
Database models module for master_electronics.

This module provides database configuration and imports all model classes
for easy access throughout the application.
"""

from dotenv import load_dotenv
import os
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

# Database configuration
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')
prod_schema = os.getenv('PROD_SCHEMA', 'production')
test_schema = os.getenv('TEST_SCHEMA', 'test')
run_mode = os.getenv('RUN_MODE', 'prod')

# Database connection
connection_string = f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require'
engine = create_engine(connection_string)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

# Schema configuration
if run_mode == 'prod':
    schema = prod_schema
    debug_mode = False
else:
    schema = test_schema
    debug_mode = True

# Table mappings
tables = {
    'products'                : f"{schema}.products",
    'part_numbers'            : f"{schema}.part_numbers",
    'manufacturers'           : f"{schema}.manufacturers",
    'categories'              : f"{schema}.categories",
    'attributes'              : f"{schema}.attributes",
    'category_attributes'     : f"{schema}.category_attributes",
    'document_media'          : f"{schema}.document_media",
    'product_sellers'         : f"{schema}.product_sellers",
    'product_attributes'      : f"{schema}.product_attributes",
    'product_extras'          : f"{schema}.product_extras",
    'automation_tasks'        : f"{schema}.automation_tasks",
    'manual_tasks'            : f"{schema}.manual_tasks"
}

# Import base and setup function
from .base import Base, setup_database

# Import all model classes
from .product import Product, PartNumber
from .manufacturer import Manufacturer
from .category import Category, CategoryAttribute
from .attribute import Attribute
from .document_media import DocumentMedia
from .product_seller import ProductSeller
from .product_attribute import ProductAttribute
from .product_extra import ProductExtra
from .automation_task import AutomationTask
from .manual_task import ManualTask

# Make all models available at module level
__all__ = [
    # Database configuration
    'engine', 'Session', 'schema', 'tables', 'debug_mode',
    
    # Base and setup
    'Base', 'setup_database',
    
    # Model classes
    'Product', 'PartNumber', 'Manufacturer', 'Category', 'CategoryAttribute',
    'Attribute', 'DocumentMedia', 'ProductSeller', 'ProductAttribute',
    'ProductExtra', 'AutomationTask', 'ManualTask'
]

# Setup function for convenience
def setup_all_tables():
    """
    Create the target schema if it doesn't exist, then create all tables
    defined on Base.metadata in that schema.
    """
    setup_database(engine=engine, schema=schema)
    print(f"Schema '{schema}' and all tables created.")

if __name__ == "__main__":
    setup_all_tables()

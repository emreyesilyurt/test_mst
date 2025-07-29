"""
Database module for master_electronics.

This module provides easy access to all database models and repositories.
You can import models and repositories directly from this module.

Example usage:
    from src.db import Product, Category, ProductRepository
    from src.db.models import Base, setup_all_tables
    from src.db.repositories import get_session
"""

# Import all models
from .models import (
    # Database configuration
    engine, Session, schema, tables, debug_mode,
    
    # Base and setup
    Base, setup_database, setup_all_tables,
    
    # Model classes
    Product, PartNumber, Manufacturer, Category, CategoryAttribute,
    Attribute, DocumentMedia, ProductSeller, ProductAttribute,
    ProductExtra, AutomationTask, ManualTask
)

# Import all repositories
from .repositories import (
    BaseRepository, ProductRepository, PartNumberRepository,
    ManufacturerRepository, CategoryRepository, AttributeRepository,
    CategoryAttributeRepository, DocumentMediaRepository,
    ProductSellerRepository, ProductAttributeRepository,
    ProductExtraRepository, ManualTaskRepository, get_session
)

# Make everything available at module level
__all__ = [
    # Database configuration
    'engine', 'Session', 'schema', 'tables', 'debug_mode',
    
    # Base and setup functions
    'Base', 'setup_database', 'setup_all_tables',
    
    # Model classes
    'Product', 'PartNumber', 'Manufacturer', 'Category', 'CategoryAttribute',
    'Attribute', 'DocumentMedia', 'ProductSeller', 'ProductAttribute',
    'ProductExtra', 'AutomationTask', 'ManualTask',
    
    # Repository classes
    'BaseRepository', 'ProductRepository', 'PartNumberRepository',
    'ManufacturerRepository', 'CategoryRepository', 'AttributeRepository',
    'CategoryAttributeRepository', 'DocumentMediaRepository',
    'ProductSellerRepository', 'ProductAttributeRepository',
    'ProductExtraRepository', 'ManualTaskRepository', 'get_session'
]

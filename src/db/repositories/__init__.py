"""
Repository module for database interactions in master_electronics.

This module provides repository classes for CRUD operations and data access logic.
All repository classes are available for import from this module.
"""

# Import all repository classes from async_repositories
from .async_repositories import (
    BaseRepository,
    ProductRepository,
    PartNumberRepository,
    ManufacturerRepository,
    CategoryRepository,
    AttributeRepository,
    CategoryAttributeRepository,
    DocumentMediaRepository,
    ProductSellerRepository,
    ProductAttributeRepository,
    ProductExtraRepository,
    ManualTaskRepository,
    get_session
)

# Make all repositories available at module level
__all__ = [
    'BaseRepository',
    'ProductRepository',
    'PartNumberRepository',
    'ManufacturerRepository',
    'CategoryRepository',
    'AttributeRepository',
    'CategoryAttributeRepository',
    'DocumentMediaRepository',
    'ProductSellerRepository',
    'ProductAttributeRepository',
    'ProductExtraRepository',
    'ManualTaskRepository',
    'get_session'
]

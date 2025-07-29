"""
Product and PartNumber models for the master_electronics database.
"""

from sqlalchemy import Column, Integer, BigInteger, Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base
from . import tables


class Product(Base):
    __tablename__ = tables.get('products').split('.')[1]
    __table_args__ = {'schema': tables.get('products').split('.')[0]}

    product_id = Column(BigInteger, primary_key=True)
    part_number = Column(Integer, ForeignKey(f"{tables.get('part_numbers')}.id"))
    category_id = Column(UUID(as_uuid=True), ForeignKey(f"{tables.get('categories')}.id"))
    manufacturer_id = Column(BigInteger, ForeignKey(f"{tables.get('manufacturers')}.id"))
    # product_series = Column(Text)
    # brand = Column(Text)
    # title = Column(Text)
    # description = Column(Text)
    # datasheet_url = Column(Text)
    # lifecycle_status = Column(Text)
    # package_type = Column(Text)
    # intro_date = Column(Text)
    # country_of_origin = Column(Text)
    # primary_image_url = Column(Text)
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())
    # compliance = Column(JSONB)

    # part_numbers = relationship('PartNumber', back_populates='product')
    manufacturer = relationship('Manufacturer', back_populates='products')
    category = relationship('Category', back_populates='products')
    document_media = relationship('DocumentMedia', back_populates='product')
    product_sellers = relationship('ProductSeller', back_populates='product')
    product_attributes = relationship('ProductAttribute', back_populates='product')
    product_extras = relationship('ProductExtra', back_populates='product')


class PartNumber(Base):
    __tablename__ = tables.get('part_numbers').split('.')[1]
    __table_args__ = {'schema': tables.get('part_numbers').split('.')[0]}

    id = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger, ForeignKey(f"{tables.get('part_numbers')}.id"))
    name = Column(Text)
    # Manual imputation fields
    notes = Column(Text)  # Notes for manual imputation processes
    source_url = Column(Text)  # Source URL for manual imputation traceability
    last_manual_update = Column(DateTime)  # Track when last manual update occurred
    manual_editor = Column(Text)  # Track who made the last manual update
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())

    # product = relationship('Product', back_populates='part_numbers')
    # manual_tasks = relationship('ManualTask', back_populates='part_number_obj')  # Removed - using product_id now

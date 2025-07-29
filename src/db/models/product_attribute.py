"""
ProductAttribute model for the master_electronics database.
"""

from sqlalchemy import Column, Integer, BigInteger, Text, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from .base import Base
from . import tables


class ProductAttribute(Base):
    __tablename__ = tables.get('product_attributes').split('.')[1]
    __table_args__ = {'schema': tables.get('product_attributes').split('.')[0]}

    id = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger, ForeignKey(f"{tables.get('products')}.product_id"))
    attribute_id = Column(BigInteger, ForeignKey(f"{tables.get('attributes')}.id"))
    value_text = Column(Text)
    value_float = Column(Float)
    value_unit = Column(Text)
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())
    source = Column(Text)
    # Task tracking - can be linked to either manual or automation task
    manual_task_id = Column(BigInteger, ForeignKey(f"{tables.get('manual_tasks')}.id"), nullable=True)
    automation_task_id = Column(BigInteger, ForeignKey(f"{tables.get('automation_tasks')}.id"), nullable=True)
    
    # Record-level tracking fields
    notes = Column(Text)  # Record-specific notes for manual imputation
    source_url = Column(Text)  # Record-specific source URL for traceability

    product = relationship('Product', back_populates='product_attributes')
    attribute = relationship('Attribute', back_populates='product_attributes')
    manual_task = relationship('ManualTask', back_populates='product_attribute_items')
    automation_task = relationship('AutomationTask', back_populates='product_attribute_items')

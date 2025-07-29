"""
Category and CategoryAttribute models for the master_electronics database.
"""

import uuid
from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, func, String, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import relationship
from .base import Base
from . import tables


class Category(Base):
    __tablename__ = tables.get('categories').split('.')[1]
    __table_args__ = {'schema': tables.get('categories').split('.')[0]}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), ForeignKey(f"{tables.get('categories')}.id"), nullable=False)
    path = Column(MutableList.as_mutable(JSONB))
    depth = Column(Integer, nullable=True)
    product_category = Column(Boolean, nullable=True)
    name = Column(String, nullable=True)
    fullname = Column(String, nullable=True)
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())

    parent_category = relationship('Category', remote_side=[id], back_populates='children')
    children = relationship('Category', back_populates='parent_category')
    products = relationship('Product', back_populates='category')
    category_attributes = relationship('CategoryAttribute', back_populates='category')


class CategoryAttribute(Base):
    __tablename__ = tables.get('category_attributes').split('.')[1]
    __table_args__ = {'schema': tables.get('category_attributes').split('.')[0]}

    id = Column(Integer, primary_key=True)
    notes = Column(Text)
    category_id = Column(UUID(as_uuid=True), ForeignKey(f"{tables.get('categories')}.id"))
    attribute_id = Column(Integer, ForeignKey(f"{tables.get('attributes')}.id"))
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())

    category = relationship('Category', back_populates='category_attributes')
    attribute = relationship('Attribute', back_populates='category_attributes')

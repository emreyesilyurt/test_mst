"""
Attribute model for the master_electronics database.
"""

from sqlalchemy import Column, Integer, Text, DateTime, func
from sqlalchemy.orm import relationship
from .base import Base
from . import tables


class Attribute(Base):
    __tablename__ = tables.get('attributes').split('.')[1]
    __table_args__ = {'schema': tables.get('attributes').split('.')[0]}

    id = Column(Integer, primary_key=True)
    name = Column(Text)
    unit = Column(Integer)
    desc = Column(Text)
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())

    category_attributes = relationship('CategoryAttribute', back_populates='attribute')
    product_attributes = relationship('ProductAttribute', back_populates='attribute')

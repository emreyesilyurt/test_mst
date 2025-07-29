"""
Manufacturer model for the master_electronics database.
"""

from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from .base import Base
from . import tables


class Manufacturer(Base):
    __tablename__ = tables.get('manufacturers').split('.')[1]
    __table_args__ = {'schema': tables.get('manufacturers').split('.')[0]}

    id = Column(Integer, primary_key=True)
    manufacturer_id = Column(Integer, ForeignKey(f"{tables.get('manufacturers')}.id"))
    name = Column(Text)
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())

    products = relationship('Product', back_populates='manufacturer')

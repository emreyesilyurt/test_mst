"""
DocumentMedia model for the master_electronics database.
"""

from sqlalchemy import Column, Integer, BigInteger, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from .base import Base
from . import tables


class DocumentMedia(Base):
    __tablename__ = tables.get('document_media').split('.')[1]
    __table_args__ = {'schema': tables.get('document_media').split('.')[0]}

    id = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger, ForeignKey(f"{tables.get('products')}.product_id"))
    url = Column(Text)
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())
    type = Column(Text)
    description = Column(Text)
    source = Column(Text)
    # Task tracking - can be linked to either manual or automation task
    manual_task_id = Column(BigInteger, ForeignKey(f"{tables.get('manual_tasks')}.id"), nullable=True)
    automation_task_id = Column(BigInteger, ForeignKey(f"{tables.get('automation_tasks')}.id"), nullable=True)
    
    # Record-level tracking fields
    notes = Column(Text)  # Record-specific notes for manual imputation
    source_url = Column(Text)  # Record-specific source URL for traceability

    product = relationship('Product', back_populates='document_media')
    manual_task = relationship('ManualTask', back_populates='document_media_items')
    automation_task = relationship('AutomationTask', back_populates='document_media_items')

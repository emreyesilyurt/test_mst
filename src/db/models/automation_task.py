"""
AutomationTask model for the master_electronics database.
"""

import time
from sqlalchemy import Column, Integer, BigInteger, Text, String, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import Base
from . import tables


class AutomationTask(Base):
    __tablename__ = tables.get('automation_tasks').split('.')[1]
    __table_args__ = {'schema': tables.get('automation_tasks').split('.')[0]}

    id = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger, ForeignKey(f"{tables.get('products')}.product_id"))  # Link to product table
    batch_id = Column(String)  # Batch identifier for grouping related tasks
    current_status = Column(String)  # 'initialized', 'processing', 'data_finished', 'supabase_finished', 'completed', 'failed'
    error_message = Column(Text)  # Store error messages if any
    
    # Consolidated timing and processing info in JSON
    processing_info = Column(JSONB)  # Contains: start_time, end_time, data_processing_time, supabase_write_time, current_step
    imputeop = Column(JSONB)  # Store the complete impute_op data from scraping (includes all results and data)
    
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    product = relationship('Product')
    document_media_items = relationship('DocumentMedia', back_populates='automation_task')
    product_seller_items = relationship('ProductSeller', back_populates='automation_task')
    product_attribute_items = relationship('ProductAttribute', back_populates='automation_task')
    product_extra_items = relationship('ProductExtra', back_populates='automation_task')

    def initialize_task(self, product_id: int, batch_id: str = None):
        """Initialize a new automation task"""
        self.product_id = product_id
        self.batch_id = batch_id or f"batch_{int(time.time())}"
        self.current_status = 'initialized'
        self.processing_info = {
            'current_step': 'initialization',
            'start_time': func.now().isoformat() if hasattr(func.now(), 'isoformat') else str(func.now())
        }
        return self

    def start_processing(self):
        """Mark task as started processing"""
        self.current_status = 'processing'
        if not self.processing_info:
            self.processing_info = {}
        self.processing_info['current_step'] = 'data_scraping'
        self.updated_date = func.now()

    def mark_data_finished(self):
        """Mark data processing as finished"""
        self.current_status = 'data_finished'
        if not self.processing_info:
            self.processing_info = {}
        self.processing_info['current_step'] = 'supabase_writing'
        self.processing_info['data_processing_time'] = func.now().isoformat() if hasattr(func.now(), 'isoformat') else str(func.now())
        self.updated_date = func.now()

    def mark_supabase_finished(self):
        """Mark supabase writing as finished"""
        self.current_status = 'supabase_finished'
        if not self.processing_info:
            self.processing_info = {}
        self.processing_info['current_step'] = 'completed'
        self.processing_info['supabase_write_time'] = func.now().isoformat() if hasattr(func.now(), 'isoformat') else str(func.now())
        self.updated_date = func.now()

    def mark_completed(self):
        """Mark task as completed"""
        self.current_status = 'completed'
        if not self.processing_info:
            self.processing_info = {}
        self.processing_info['current_step'] = 'finished'
        self.processing_info['end_time'] = func.now().isoformat() if hasattr(func.now(), 'isoformat') else str(func.now())
        self.updated_date = func.now()

    def mark_failed(self, error_message: str):
        """Mark task as failed with error message"""
        self.current_status = 'failed'
        self.error_message = error_message
        if not self.processing_info:
            self.processing_info = {}
        self.processing_info['end_time'] = func.now().isoformat() if hasattr(func.now(), 'isoformat') else str(func.now())
        self.updated_date = func.now()

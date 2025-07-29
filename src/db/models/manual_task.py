"""
ManualTask model for tracking manual data imputation tasks.
This module contains the ManualTask model for manual data editing and tracking.
"""

import time
from sqlalchemy import Column, Integer, BigInteger, Text, String, DateTime, func, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.future import select
from .base import Base
from . import tables
from src.db.connections import get_supabase_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker


class ManualTask(Base):
    __tablename__ = tables.get('manual_tasks').split('.')[1]
    __table_args__ = {'schema': tables.get('manual_tasks').split('.')[0]}

    id = Column(BigInteger, primary_key=True)
    product_id = Column(BigInteger, ForeignKey(f"{tables.get('products')}.product_id"))  # Link to product table
    batch_id = Column(String)  # Batch identifier for grouping related tasks
    current_status = Column(String)  # 'initialized', 'processing', 'data_finished', 'supabase_finished', 'completed', 'failed'
    error_message = Column(Text)  # Store error messages if any
    
    # Manual task specific fields
    editor = Column(String, nullable=False)
    task_type = Column(String, default='manual_imputation')
    validated = Column(Boolean, default=False)
    validator = Column(String)
    validation_date = Column(DateTime)
    note = Column(Text)
    source_url = Column(String)
    
    # Consolidated timing and processing info in JSON
    processing_info = Column(JSONB)  # Contains: start_time, end_time, data_processing_time, supabase_write_time, current_step
    edited_fields = Column(JSONB)  # Track which fields were edited
    affected_tables = Column(JSONB)  # Track which tables were affected
    changes_summary = Column(JSONB)  # Summary of changes made
    
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    product = relationship('Product')
    document_media_items = relationship('DocumentMedia', back_populates='manual_task')
    product_seller_items = relationship('ProductSeller', back_populates='manual_task')
    product_attribute_items = relationship('ProductAttribute', back_populates='manual_task')
    product_extra_items = relationship('ProductExtra', back_populates='manual_task')

    def initialize_task(self, product_id: int, editor: str, batch_id: str = None):
        """Initialize a new manual task"""
        self.product_id = product_id
        self.editor = editor
        self.batch_id = batch_id or f"manual_batch_{int(time.time())}"
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
        self.processing_info['current_step'] = 'manual_editing'
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
        self.processing_info['current_step'] = 'validation_pending'
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

    def mark_validated(self, validator: str):
        """Mark task as validated"""
        self.validated = True
        self.validator = validator
        self.validation_date = func.now()
        self.updated_date = func.now()

# ---------- DB Helper Functions ----------

async def get_task_by_id_db(task_id: int):
    async_engine = get_supabase_async_engine()
    async_session = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(select(ManualTask).filter(ManualTask.id == task_id))
        task = result.scalar_one_or_none()
        return task


async def update_task_metadata_db(task_id: int, note: str = None, source_url: str = None):
    async_engine = get_supabase_async_engine()
    async_session = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    async with async_session() as session:
        task = await get_task_by_id_db(task_id)
        if not task:
            return False
        if note:
            task.note = note
        if source_url:
            task.source_url = source_url
        task.updated_date = func.now()
        await session.commit()
        return True


async def delete_task_db(task_id: int):
    async_engine = get_supabase_async_engine()
    async_session = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    async with async_session() as session:
        task = await get_task_by_id_db(task_id)
        if not task:
            return False
        await session.delete(task)
        await session.commit()
        return True

"""
Base model configuration and common imports for all database models.
"""

from sqlalchemy import Column, Integer, Text, Float, String, TIMESTAMP, ForeignKey, func, DateTime, Boolean
import uuid
import time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from . import tables, schema, text, engine
from src.db.connections import get_supabase_engine

# Use the engine from database configuration
# engine = get_supabase_engine()

Base = declarative_base()

def setup_database(engine, schema):
    """
    Create the target schema if it doesn't exist, then create all tables
    defined on Base.metadata in that schema.
    """
    Base.metadata.create_all(bind=engine)

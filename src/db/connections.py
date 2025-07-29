"""
Database connection management for master_electronics.

This module provides functions to create database engines and clients for BigQuery 
and Supabase PostgreSQL database using SQLAlchemy and Google Cloud BigQuery client.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from google.cloud import bigquery

# Load environment variables from .env file
load_dotenv()

# Environment variables for database credentials
BIGQUERY_PROJECT_ID = os.getenv("BIGQUERY_PROJECT_ID", "your-project-id")
BIGQUERY_CREDENTIALS_PATH = os.getenv("BIGQUERY_CREDENTIALS_PATH", "path/to/credentials.json")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "your-dataset")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE", "your-table")
DB_HOST = os.getenv("DB_HOST", "your-supabase-host")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "your-supabase-user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your-supabase-password")


def get_bigquery_client():
    """
    Create and return a BigQuery client using credentials from environment variables or a file.
    
    Returns:
        bigquery.Client: A configured BigQuery client for use with pandas_gbq.
        
    Raises:
        Exception: If credentials file doesn't exist and default credentials fail.
    """
    try:
        if os.path.exists(BIGQUERY_CREDENTIALS_PATH):
            client = bigquery.Client.from_service_account_json(
                BIGQUERY_CREDENTIALS_PATH, 
                project=BIGQUERY_PROJECT_ID
            )
        else:
            client = bigquery.Client(project=BIGQUERY_PROJECT_ID)
        return client
    except Exception as e:
        print(f"Error creating BigQuery client: {str(e)}")
        print("Please check your BigQuery credentials and project configuration.")
        raise


def get_supabase_engine():
    """
    Create and return a SQLAlchemy engine for Supabase PostgreSQL database.
    
    Returns:
        sqlalchemy.engine.Engine: A configured SQLAlchemy engine for Supabase.
        
    Raises:
        Exception: If connection parameters are invalid or connection fails.
    """
    try:
        connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(connection_string)
        return engine
    except Exception as e:
        print(f"Error creating Supabase engine: {str(e)}")
        print("Please check your Supabase connection parameters.")
        raise


def get_supabase_async_engine():
    """
    Create and return an async SQLAlchemy engine for Supabase PostgreSQL database.
    
    Returns:
        sqlalchemy.ext.asyncio.AsyncEngine: A configured async SQLAlchemy engine for Supabase.
        
    Raises:
        Exception: If there is a network or configuration issue preventing connection.
    """
    try:
        connection_string = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_async_engine(
            connection_string,
            pool_size=5,  # Limit the number of connections in the pool
            max_overflow=10,  # Allow up to 10 additional connections beyond pool_size
            pool_timeout=30,  # Wait up to 30 seconds for a connection
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Validate connections before use
            echo=False  # Set to True for debugging SQL queries
        )
        return engine
    except Exception as e:
        print(f"Error creating async engine for Supabase: {str(e)}")
        print("This appears to be a network issue. Please check your internet connection or DNS settings.")
        print(f"Ensure that the hostname '{DB_HOST}' can be resolved and is accessible.")
        raise


def get_database_config():
    """
    Get database configuration parameters.
    
    Returns:
        dict: Dictionary containing database configuration parameters.
    """
    return {
        'bigquery': {
            'project_id': BIGQUERY_PROJECT_ID,
            'credentials_path': BIGQUERY_CREDENTIALS_PATH,
            'dataset': BIGQUERY_DATASET,
            'table': BIGQUERY_TABLE
        },
        'supabase': {
            'host': DB_HOST,
            'port': DB_PORT,
            'database': DB_NAME,
            'user': DB_USER,
            'password': DB_PASSWORD
        }
    }

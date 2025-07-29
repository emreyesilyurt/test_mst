#!/usr/bin/env python3
"""
Simple Production Database Setup

This script uses the existing setup_all_tables() function from your models
to initialize the production database.
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append('src')

# Load environment variables
load_dotenv()

def main():
    """Initialize production database using existing setup function."""
    
    print("Setting up production database...")
    print(f"Current RUN_MODE: {os.getenv('RUN_MODE')}")
    
    # Ensure we're in production mode
    os.environ['RUN_MODE'] = 'prod'
    print(f"Set RUN_MODE to: {os.getenv('RUN_MODE')}")
    
    try:
        # Import and run the setup function
        from db.models import setup_all_tables, schema, tables
        
        print(f"Target schema: {schema}")
        print("Tables to be created:")
        for table_name, full_name in tables.items():
            print(f"  - {full_name}")
        
        # Create all tables
        setup_all_tables()
        
        print("Production database setup completed successfully!")
        
    except Exception as e:
        print(f"Error setting up production database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

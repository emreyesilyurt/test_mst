"""
BigQuery service module for master_electronics.

This module provides functions to interact with BigQuery tables, specifically
for fetching part number (PN) data and other product information used in
automation processes.
"""

from typing import Optional, List, Dict, Any
import pandas as pd
from src.db.connections import get_bigquery_client, get_database_config


class BigQueryService:
    """
    Service class for BigQuery operations.
    
    This class encapsulates all BigQuery-related functionality including
    data fetching, querying, and result processing.
    """
    
    def __init__(self):
        """Initialize BigQuery service with client and configuration."""
        self.client = get_bigquery_client()
        self.config = get_database_config()['bigquery']
        self.project_id = self.config['project_id']
        self.dataset = self.config['dataset']
        self.table = self.config['table']
    
    def fetch_all_data_sorted(self, limit: int = 100, priority_threshold: Optional[float] = None) -> pd.DataFrame:
        """
        Fetch part number data from BigQuery based on priority score.
        
        This function retrieves data from the configured BigQuery table,
        filtering by priority score and ordering by score in descending order.
        
        Args:
            limit: Maximum number of records to fetch (default: 100)
            priority_threshold: Minimum priority score threshold (optional)
            
        Returns:
            pd.DataFrame: DataFrame containing the fetched data
            
        Raises:
            Exception: If BigQuery query fails or connection issues occur
        """
        try:
            # Build the base query
            query = f"""
                SELECT *
                FROM `{self.project_id}.{self.dataset}.{self.table}`
                WHERE priority_score.score IS NOT NULL
            """
            
            # Add priority threshold filter if specified
            if priority_threshold is not None:
                query += f" AND priority_score.score >= {priority_threshold}"
            
            # Add ordering and limit
            query += f"""
                ORDER BY priority_score.score DESC
                LIMIT {limit}
            """
            
            print(f"Executing BigQuery query with limit: {limit}")
            if priority_threshold:
                print(f"Using priority threshold: {priority_threshold}")
            
            # Execute query and return DataFrame
            df = self.client.query(query).to_dataframe()
            print(f"Successfully fetched {len(df)} records from BigQuery")
            
            return df
            
        except Exception as e:
            print(f"Error fetching data from BigQuery: {str(e)}")
            print("Please check your BigQuery configuration and network connection.")
            raise
    
    def fetch_by_part_numbers(self, part_numbers: List[str], limit: int = 1000) -> pd.DataFrame:
        """
        Fetch data for specific part numbers from BigQuery.
        
        Args:
            part_numbers: List of part numbers to fetch
            limit: Maximum number of records to fetch (default: 1000)
            
        Returns:
            pd.DataFrame: DataFrame containing the fetched data for specified part numbers
        """
        try:
            if not part_numbers:
                return pd.DataFrame()
            
            # Create comma-separated string of quoted part numbers for SQL IN clause
            pn_list = "', '".join(part_numbers)
            
            query = f"""
                SELECT *
                FROM `{self.project_id}.{self.dataset}.{self.table}`
                WHERE pn IN ('{pn_list}')
                LIMIT {limit}
            """
            
            print(f"Fetching data for {len(part_numbers)} part numbers from BigQuery")
            df = self.client.query(query).to_dataframe()
            print(f"Successfully fetched {len(df)} records for specified part numbers")
            
            return df
            
        except Exception as e:
            print(f"Error fetching part numbers from BigQuery: {str(e)}")
            raise
    
    def fetch_by_manufacturer(self, manufacturer: str, limit: int = 500) -> pd.DataFrame:
        """
        Fetch data for a specific manufacturer from BigQuery.
        
        Args:
            manufacturer: Manufacturer name to filter by
            limit: Maximum number of records to fetch (default: 500)
            
        Returns:
            pd.DataFrame: DataFrame containing the fetched data for the manufacturer
        """
        try:
            query = f"""
                SELECT *
                FROM `{self.project_id}.{self.dataset}.{self.table}`
                WHERE manufacturer = '{manufacturer}'
                ORDER BY priority_score.score DESC
                LIMIT {limit}
            """
            
            print(f"Fetching data for manufacturer: {manufacturer}")
            df = self.client.query(query).to_dataframe()
            print(f"Successfully fetched {len(df)} records for manufacturer: {manufacturer}")
            
            return df
            
        except Exception as e:
            print(f"Error fetching manufacturer data from BigQuery: {str(e)}")
            raise
    
    def get_unique_manufacturers(self, limit: int = 100) -> List[str]:
        """
        Get list of unique manufacturers from BigQuery table.
        
        Args:
            limit: Maximum number of manufacturers to return (default: 100)
            
        Returns:
            List[str]: List of unique manufacturer names
        """
        try:
            query = f"""
                SELECT DISTINCT manufacturer
                FROM `{self.project_id}.{self.dataset}.{self.table}`
                WHERE manufacturer IS NOT NULL AND manufacturer != ''
                ORDER BY manufacturer
                LIMIT {limit}
            """
            
            df = self.client.query(query).to_dataframe()
            manufacturers = df['manufacturer'].tolist()
            print(f"Found {len(manufacturers)} unique manufacturers")
            
            return manufacturers
            
        except Exception as e:
            print(f"Error fetching manufacturers from BigQuery: {str(e)}")
            raise
    
    def get_table_stats(self) -> Dict[str, Any]:
        """
        Get basic statistics about the BigQuery table.
        
        Returns:
            Dict[str, Any]: Dictionary containing table statistics
        """
        try:
            query = f"""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT pn) as unique_part_numbers,
                    COUNT(DISTINCT manufacturer) as unique_manufacturers,
                    AVG(priority_score.score) as avg_priority_score,
                    MAX(priority_score.score) as max_priority_score,
                    MIN(priority_score.score) as min_priority_score
                FROM `{self.project_id}.{self.dataset}.{self.table}`
                WHERE priority_score.score IS NOT NULL
            """
            
            df = self.client.query(query).to_dataframe()
            stats = df.iloc[0].to_dict()
            
            print("BigQuery table statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            return stats
            
        except Exception as e:
            print(f"Error fetching table statistics from BigQuery: {str(e)}")
            raise


# Convenience functions for backward compatibility
def fetch_all_data_sorted(limit: int = 100) -> pd.DataFrame:
    """
    Convenience function to fetch sorted data from BigQuery.
    
    This function maintains backward compatibility with existing code
    that uses the original fetch_all_data_sorted function.
    
    Args:
        limit: Maximum number of records to fetch (default: 100)
        
    Returns:
        pd.DataFrame: DataFrame containing the fetched data
    """
    service = BigQueryService()
    return service.fetch_all_data_sorted(limit=limit)


def get_bigquery_service() -> BigQueryService:
    """
    Factory function to create and return a BigQueryService instance.
    
    Returns:
        BigQueryService: Configured BigQuery service instance
    """
    return BigQueryService()

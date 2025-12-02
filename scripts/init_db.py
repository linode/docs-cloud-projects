#!/usr/bin/env python3
"""
Database initialization script for the LangChain RAG Chatbot.
Creates necessary tables and indexes in both PostgreSQL databases.
"""

import logging
import sys
import os
from typing import List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import get_settings, validate_environment
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles database initialization for both vector and state databases."""
    
    def __init__(self):
        """Initialize the database initializer."""
        self.settings = get_settings()
        
        # Validate environment variables
        if not validate_environment():
            logger.error("Environment validation failed")
            sys.exit(1)
    
    def initialize_vector_database(self) -> bool:
        """
        Initialize the vector database with pgvector extension and tables.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Initializing vector database...")
            
            conn = psycopg2.connect(self.settings.vector_db_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            logger.info("Enabling pgvector extension...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Note: PGVector will create its own tables automatically when first used
            logger.info("PGVector tables will be created automatically when documents are first added")
            
            cursor.close()
            conn.close()
            
            logger.info("Vector database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            return False
    
    def initialize_state_database(self) -> bool:
        """
        Initialize the state database for LangGraph checkpointing.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Initializing state database...")
            
            conn = psycopg2.connect(self.settings.state_db_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            logger.info("Creating checkpoints table...")
            # Drop existing table if it has old schema
            cursor.execute("DROP TABLE IF EXISTS checkpoints CASCADE;")
            
            # Create the checkpoints table with the correct schema for langgraph-checkpoint-postgres 1.0.0
            cursor.execute("""
                CREATE TABLE checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL DEFAULT '',
                    checkpoint_id TEXT NOT NULL,
                    checkpoint JSONB NOT NULL,
                    metadata JSONB,
                    parent_checkpoint_id TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                );
            """)
            
            logger.info("Creating state database indexes...")
            
            # Index on thread_id for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id 
                ON checkpoints (thread_id);
            """)
            
            # Index on parent_checkpoint_id for checkpoint chains
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_parent 
                ON checkpoints (parent_checkpoint_id);
            """)
            
            # Index on created_at for cleanup operations
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_created_at 
                ON checkpoints (created_at);
            """)
            
            # Composite index for efficient lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_ns 
                ON checkpoints (thread_id, checkpoint_ns);
            """)
            
            logger.info("Creating cleanup function...")
            cursor.execute("""
                CREATE OR REPLACE FUNCTION cleanup_old_checkpoints(days_to_keep INTEGER DEFAULT 30)
                RETURNS INTEGER AS $$
                DECLARE
                    deleted_count INTEGER;
                BEGIN
                    DELETE FROM checkpoints 
                    WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
                    
                    GET DIAGNOSTICS deleted_count = ROW_COUNT;
                    RETURN deleted_count;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            cursor.close()
            conn.close()
            
            logger.info("State database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize state database: {e}")
            return False
    
    def test_connections(self) -> Dict[str, bool]:
        """
        Test connections to both databases.
        
        Returns:
            Dict with connection status for each database
        """
        results = {
            "vector_db": False,
            "state_db": False
        }
        
        try:
            conn = psycopg2.connect(self.settings.vector_db_url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            cursor.close()
            conn.close()
            results["vector_db"] = True
            logger.info("Vector database connection: OK")
        except Exception as e:
            logger.error(f"Vector database connection failed: {e}")
        
        try:
            conn = psycopg2.connect(self.settings.state_db_url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            cursor.close()
            conn.close()
            results["state_db"] = True
            logger.info("State database connection: OK")
        except Exception as e:
            logger.error(f"State database connection failed: {e}")
        
        return results
    
    def run_initialization(self) -> bool:
        """
        Run the complete database initialization process.
        
        Returns:
            bool: True if all initializations were successful
        """
        logger.info("Starting database initialization...")
        
        # Test connections first
        connections = self.test_connections()
        if not connections["vector_db"] or not connections["state_db"]:
            logger.error("Database connections failed. Please check your configuration.")
            return False
        
        # Initialize vector database
        if not self.initialize_vector_database():
            logger.error("Vector database initialization failed")
            return False
        
        # Initialize state database
        if not self.initialize_state_database():
            logger.error("State database initialization failed")
            return False
        
        logger.info("Database initialization completed successfully!")
        return True


def main():
    """Main entry point for the database initialization script."""
    logger.info("LangChain RAG Chatbot - Database Initialization")
    
    try:
        initializer = DatabaseInitializer()
        success = initializer.run_initialization()
        
        if success:
            logger.info("Database initialization completed successfully!")
            print("\nDatabase initialization completed successfully!")
            sys.exit(0)
        else:
            logger.error("Database initialization failed")
            print("\nDatabase initialization failed. Check the logs above for details.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {e}")
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Document indexing script for the LangChain RAG Chatbot.
Indexes all documents in the S3 bucket into the vector database.
"""

import logging
import sys
import os
import boto3
from typing import List, Dict, Any, Optional
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import get_settings, validate_environment
from app.core.rag import get_rag_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Handles indexing of documents from S3-compatible Object Storage."""
    
    def __init__(self):
        """Initialize the document indexer."""
        self.settings = get_settings()
        
        if not validate_environment():
            logger.error("Environment validation failed")
            sys.exit(1)
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.settings.linode_object_storage_endpoint,
            aws_access_key_id=self.settings.linode_object_storage_access_key,
            aws_secret_access_key=self.settings.linode_object_storage_secret_key
        )
        
        self.rag_pipeline = get_rag_pipeline()
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all documents in the Object Storage bucket.
        
        Returns:
            List of document information dictionaries
        """
        try:
            logger.info("Listing documents in Object Storage...")
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.settings.linode_object_storage_bucket
            )
            
            documents = []
            for obj in response.get('Contents', []):
                documents.append({
                    "object_key": obj['Key'],
                    "filename": obj['Key'].split('/')[-1],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'],
                    "etag": obj['ETag']
                })
            
            logger.info(f"Found {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    def index_documents(self, object_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Index documents from Object Storage into the vector database.
        
        Args:
            object_keys: Optional list of specific object keys to index.
                        If None, indexes all documents.
        
        Returns:
            Dictionary with indexing results
        """
        try:
            if object_keys is None:
                # Get all documents
                documents = self.list_documents()
                object_keys = [doc["object_key"] for doc in documents]
            
            if not object_keys:
                return {
                    "success": True,
                    "documents_processed": 0,
                    "chunks_created": 0,
                    "message": "No documents to index"
                }
            
            logger.info(f"Indexing {len(object_keys)} documents...")
            
            result = self.rag_pipeline.index_documents_from_s3(object_keys)
            
            logger.info(f"Indexing completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to index documents: {e}")
            return {
                "success": False,
                "documents_processed": 0,
                "chunks_created": 0,
                "message": f"Failed to index documents: {str(e)}"
            }
    
    
    def test_object_storage_connection(self) -> bool:
        """
        Test connection to Linode Object Storage.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            logger.info("Testing Object Storage connection...")
            
            # This will fail if bucket doesn't exist or no access
            self.s3_client.head_bucket(Bucket=self.settings.linode_object_storage_bucket)
            
            logger.info("Object Storage connection: OK")
            return True
            
        except Exception as e:
            logger.error(f"Object Storage connection failed: {e}")
            return False
    
    def run_full_indexing(self, start_at: int = 0) -> bool:
        """
        Run full indexing of all documents in Object Storage.
        
        Args:
            start_at: Index to start indexing from (0-based)
        
        Returns:
            bool: True if successful
        """
        try:
            logger.info("Starting full document indexing...")
            
            # Test Object Storage connection
            if not self.test_object_storage_connection():
                logger.error("Object Storage connection failed")
                return False
            
            documents = self.list_documents()
            
            if not documents:
                logger.info("No documents found in Object Storage")
                return True
            
            object_keys = [doc["object_key"] for doc in documents]
            
            # Apply start_at filter
            if start_at > 0:
                if start_at >= len(object_keys):
                    logger.error(f"Start index {start_at} is beyond the number of documents ({len(object_keys)})")
                    return False
                object_keys = object_keys[start_at:]
                logger.info(f"Starting from document {start_at + 1}, processing {len(object_keys)} documents")
            
            logger.info(f"Found {len(object_keys)} documents to index")
            
            # Index all documents
            result = self.index_documents(object_keys)
            
            if result["success"]:
                logger.info(f"Successfully indexed {result['documents_processed']} documents")
                logger.info(f"Created {result['chunks_created']} text chunks")
                return True
            else:
                logger.error(f"Indexing failed: {result['message']}")
                return False
                
        except Exception as e:
            logger.error(f"Full indexing failed: {e}")
            return False


def main():
    """Main entry point for the document indexing script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Document indexing for LangChain RAG Chatbot")
    parser.add_argument("--list", "-l", action="store_true", help="List all documents in Object Storage")
    parser.add_argument("--index-all", "-a", action="store_true", help="Index all documents in Object Storage")
    parser.add_argument("--test", "-t", action="store_true", help="Test Object Storage connection")
    parser.add_argument("--start-at", "-s", type=int, default=0, help="Start indexing from this document index (0-based)")
    
    args = parser.parse_args()
    
    logger.info("LangChain RAG Chatbot - Document Indexing")
    
    try:
        indexer = DocumentIndexer()
        
        if args.test:
            success = indexer.test_object_storage_connection()
            if success:
                print("Object Storage connection test passed!")
            else:
                print("Object Storage connection test failed!")
            sys.exit(0 if success else 1)
        
        elif args.list:
            documents = indexer.list_documents()
            if documents:
                print(f"\nFound {len(documents)} documents:")
                for doc in documents:
                    print(f"  - {doc['filename']} ({doc['size']} bytes)")
            else:
                print("\nNo documents found in Object Storage")
            sys.exit(0)
        
        elif args.index_all:
            success = indexer.run_full_indexing(start_at=args.start_at)
            if success:
                print("\nFull document indexing completed successfully!")
            else:
                print("\nFull document indexing failed!")
            sys.exit(0 if success else 1)
        
        else:
            # Default: Index all documents in the bucket
            logger.info("No specific options provided. Indexing all documents in the bucket...")
            success = indexer.run_full_indexing(start_at=args.start_at)
            if success:
                print("\nFull document indexing completed successfully!")
            else:
                print("\nFull document indexing failed!")
            sys.exit(0 if success else 1)
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

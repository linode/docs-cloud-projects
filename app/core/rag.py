"""
RAG (Retrieval-Augmented Generation) pipeline implementation using LangChain.
Handles document indexing, vector storage, and query processing.
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector
from langchain_community.document_loaders import S3FileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGPipeline:
    """RAG pipeline for document retrieval and question answering."""
    
    def __init__(self):
        """Initialize the RAG pipeline components."""
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key
        )
        
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            openai_api_key=settings.openai_api_key,
            temperature=0.1
        )
        
        self.vector_store = None
        self.retriever = None
        self.rag_chain = None
        
        self._initialize_vector_store()
        self._create_rag_chain()
    
    def _initialize_vector_store(self):
        """Initialize the PostgreSQL vector store."""
        try:
            self.vector_store = PGVector(
                connection=settings.vector_db_url,
                embeddings=self.embeddings,
                collection_name="documents"
            )
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def _create_rag_chain(self):
        """Create the RAG chain for question answering."""
        try:
            # Create retriever
            self.retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": settings.retrieval_k}
            )
            
            # Define the RAG prompt template
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful assistant that answers questions based on the provided context. 
                
                Instructions:
                - Answer questions using ONLY the information provided in the context documents
                - Always cite your sources when referencing specific information
                - Include the document title, author, and source file when citing
                - Cite the source file as the original document name, not the chunk index or document number
                - Don't cite the document number (like "Document 1" or "Document 2") as this is not useful information
                - If the context doesn't contain relevant information, say so clearly
                - Be concise but comprehensive in your answers
                - Maintain a helpful and professional tone
                
                When citing sources, use this format: "According to [Title] by [Author] ([Source file])..." or "As mentioned in [Title] by [Author]..."."""),
                ("human", "Context:\n{context}\n\nQuestion: {question}")
            ])
            
            # Create the RAG chain using LangChain Expression Language (LCEL)
            self.rag_chain = (
                {"context": self.retriever | self._format_docs, "question": RunnablePassthrough()}
                | prompt_template
                | self.llm
                | StrOutputParser()
            )
            
            logger.info("RAG chain created successfully")
        except Exception as e:
            logger.error(f"Failed to create RAG chain: {e}")
            raise
    
    def _format_docs(self, docs: List[Document]) -> str:
        """Format retrieved documents for the prompt with source attribution."""
        formatted_docs = []
        
        for i, doc in enumerate(docs, 1):
            # Extract metadata
            title = doc.metadata.get("title", "Unknown Title")
            author = doc.metadata.get("author", "Unknown Author")
            source = doc.metadata.get("source", "unknown")
            chunk_index = doc.metadata.get("chunk_index", 0)
            total_chunks = doc.metadata.get("total_chunks", 0)
            
            # Format with source information
            doc_header = f"--- {title} by {author} ---"
            doc_source = f"Source: {source} (chunk {chunk_index + 1} of {total_chunks})"
            doc_content = doc.page_content
            
            formatted_doc = f"{doc_header}\n{doc_source}\n\n{doc_content}"
            formatted_docs.append(formatted_doc)
        
        return "\n\n".join(formatted_docs)
    
    def index_documents_from_s3(self, object_keys: List[str]) -> Dict[str, Any]:
        """
        Index documents from S3-compatible Object Storage.
        
        Args:
            object_keys: List of object keys in the S3 bucket
            
        Returns:
            Dictionary with indexing results
        """
        try:
            total_chunks = 0
            processed_docs = 0
            
            for object_key in object_keys:
                logger.info(f"Processing document: {object_key}")
                
                # Load document from S3
                loader = S3FileLoader(
                    bucket=settings.linode_object_storage_bucket,
                    key=object_key,
                    aws_access_key_id=settings.linode_object_storage_access_key,
                    aws_secret_access_key=settings.linode_object_storage_secret_key,
                    endpoint_url=settings.linode_object_storage_endpoint
                )
                
                documents = loader.load()
                
                if not documents:
                    logger.warning(f"No content found in document: {object_key}")
                    continue
                
                # Split documents into chunks
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap,
                    length_function=len,
                    separators=["\n\n", "\n", " ", ""]
                )
                
                chunks = text_splitter.split_documents(documents)
                
                # Extract enhanced metadata from document
                enhanced_metadata = self._extract_document_metadata(object_key, documents[0])
                
                # Log the extracted metadata
                logger.info(f"Extracted metadata for {object_key}:")
                if enhanced_metadata.get("title"):
                    logger.info(f"  Title: {enhanced_metadata['title']}")
                if enhanced_metadata.get("author"):
                    logger.info(f"  Author: {enhanced_metadata['author']}")
                if enhanced_metadata.get("language"):
                    logger.info(f"  Language: {enhanced_metadata['language']}")
                logger.info(f"  Document Type: {enhanced_metadata.get('document_type', 'unknown')}")
                logger.info(f"  Document Length: {enhanced_metadata.get('document_length', 0):,} characters")
                logger.info(f"  Indexed At: {enhanced_metadata.get('indexed_at', 'unknown')}")
                
                # Add metadata to chunks
                for i, chunk in enumerate(chunks):
                    chunk.metadata.update({
                        "source": object_key,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        **enhanced_metadata  # Spread enhanced metadata
                    })
                
                # Store chunks in vector database
                self.vector_store.add_documents(chunks)
                
                total_chunks += len(chunks)
                processed_docs += 1
                
                logger.info(f"Successfully indexed {len(chunks)} chunks from {object_key}")
                logger.info(f"  Chunk size: {settings.chunk_size} chars, overlap: {settings.chunk_overlap} chars")
            
            # Create vector index for better performance after all documents are added
            if total_chunks > 0:
                logger.info("Creating vector indexes for better search performance...")
                self._create_vector_index()
            
            result = {
                "success": True,
                "documents_processed": processed_docs,
                "chunks_created": total_chunks,
                "message": f"Successfully indexed {processed_docs} documents with {total_chunks} chunks"
            }
            
            logger.info(f"Document indexing completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to index documents: {e}")
            return {
                "success": False,
                "documents_processed": 0,
                "chunks_created": 0,
                "message": f"Failed to index documents: {str(e)}"
            }
    
    def _extract_document_metadata(self, object_key: str, document) -> Dict[str, Any]:
        """
        Extract enhanced metadata from document preamble/top section.
        
        Args:
            object_key: The S3 object key (filename)
            document: The loaded document object
            
        Returns:
            Dictionary with enhanced metadata
        """
        metadata = {}
        
        try:
            # Extract filename info as fallback
            filename = object_key.split('/')[-1]
            
            # Extract document type from extension
            if '.' in filename:
                ext = filename.split('.')[-1].lower()
                if ext in ['txt', 'md', 'rst']:
                    metadata["document_type"] = "text"
                elif ext in ['pdf']:
                    metadata["document_type"] = "pdf"
                elif ext in ['doc', 'docx']:
                    metadata["document_type"] = "word"
                else:
                    metadata["document_type"] = ext
            else:
                metadata["document_type"] = "unknown"
            
            # Parse document preamble/top section
            content = document.page_content[:2000]  # First 2000 chars for preamble
            metadata.update(self._parse_document_preamble(content))
            
            # Add document length
            metadata["document_length"] = len(document.page_content)
            
            # Add processing timestamp
            from datetime import datetime
            metadata["indexed_at"] = datetime.now().isoformat()
            
            logger.debug(f"Extracted metadata for {object_key}: {metadata}")
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata for {object_key}: {e}")
            # Fallback metadata
            metadata = {
                "title": filename,
                "document_type": "unknown",
                "indexed_at": datetime.now().isoformat()
            }
        
        return metadata
    
    def _parse_document_preamble(self, content: str) -> Dict[str, Any]:
        """
        Parse document preamble/top section to extract basic metadata.
        Works with various document formats and preamble styles.
        
        Args:
            content: First portion of document content containing preamble
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}
        
        try:
            import re
            
            # Extract title from "Title: ..." line (common in many document formats)
            title_match = re.search(r'Title:\s*(.+?)(?:\n|$)', content, re.IGNORECASE | re.MULTILINE)
            if title_match:
                metadata["title"] = title_match.group(1).strip()
            
            # Extract author from "Author: ..." line (common in many document formats)
            author_match = re.search(r'Author:\s*(.+?)(?:\n|$)', content, re.IGNORECASE | re.MULTILINE)
            if author_match:
                metadata["author"] = author_match.group(1).strip()
            
            # Extract language from "Language: ..." line (common in many document formats)
            language_match = re.search(r'Language:\s*(.+?)(?:\n|$)', content, re.IGNORECASE | re.MULTILINE)
            if language_match:
                metadata["language"] = language_match.group(1).strip().lower()
            
            logger.debug(f"Parsed document preamble metadata: {metadata}")
            
        except Exception as e:
            logger.warning(f"Failed to parse document preamble: {e}")
        
        return metadata

    def _create_vector_index(self):
        """Create HNSW index for faster vector similarity search."""
        try:
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
            
            # Connect to database and create index
            conn = psycopg2.connect(settings.vector_db_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # First, check if the embedding column exists and has data
            cursor.execute("""
                SELECT COUNT(*) FROM langchain_pg_embedding WHERE embedding IS NOT NULL;
            """)
            embedding_count = cursor.fetchone()[0]
            
            if embedding_count == 0:
                logger.info("No embeddings found, skipping index creation")
                cursor.close()
                conn.close()
                return
            
            # Check if the embedding column is already a vector type
            cursor.execute("""
                SELECT data_type FROM information_schema.columns 
                WHERE table_name = 'langchain_pg_embedding' AND column_name = 'embedding';
            """)
            column_info = cursor.fetchone()
            
            if not column_info:
                logger.warning("Embedding column not found, skipping index creation")
                cursor.close()
                conn.close()
                return
            
            column_type = column_info[0]
            logger.info(f"Embedding column type: {column_type}")
            
            # If the column is not a vector type, we need to convert it
            if 'vector' not in column_type.lower():
                logger.info("Converting embedding column to vector type...")
                
                # Get the actual embedding dimension from the embedding model
                try:
                    # Create a test embedding to get the correct dimension
                    test_embedding = self.embeddings.embed_query("test")
                    correct_dimension = len(test_embedding)
                    logger.info(f"Using embedding dimension from model: {correct_dimension}")
                except Exception as e:
                    logger.warning(f"Could not get dimension from embedding model: {e}")
                    correct_dimension = 1536  # Default for text-embedding-3-small
                
                # Convert the string representation to proper vector type
                logger.info(f"Converting string embeddings to vector({correct_dimension}) type")
                cursor.execute(f"""
                    ALTER TABLE langchain_pg_embedding 
                    ALTER COLUMN embedding TYPE vector({correct_dimension}) 
                    USING CASE 
                        WHEN embedding::text ~ '^\\[.*\\]$' THEN 
                            embedding::text::vector({correct_dimension})
                        ELSE 
                            NULL::vector({correct_dimension})
                    END;
                """)
            
            # Now create the indexes
            logger.info("Creating HNSW index for vector similarity search...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS langchain_pg_embedding_embedding_hnsw_idx 
                ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """)
            
            logger.info("Creating GIN index on metadata for filtering...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS langchain_pg_embedding_cmetadata_idx 
                ON langchain_pg_embedding USING gin (cmetadata);
            """)
            
            logger.info("Vector indexes created successfully")
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Could not create vector index: {e}")
            # Don't raise the exception, just log it as a warning

    def query(self, question: str) -> Dict[str, Any]:
        """
        Query the RAG system with a question.
        
        Args:
            question: The user's question
            
        Returns:
            Dictionary with the answer and metadata
        """
        try:
            # Get the answer from the RAG chain
            answer = self.rag_chain.invoke(question)
            
            # Get retrieved documents for context
            retrieved_docs = self.retriever.get_relevant_documents(question)
            
            result = {
                "answer": answer,
                "sources": [
                    {
                        "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        "source": doc.metadata.get("source", "unknown"),
                        "title": doc.metadata.get("title", "Unknown Title"),
                        "author": doc.metadata.get("author", "Unknown Author"),
                        "language": doc.metadata.get("language", "unknown"),
                        "document_type": doc.metadata.get("document_type", "unknown"),
                        "chunk_index": doc.metadata.get("chunk_index", 0),
                        "total_chunks": doc.metadata.get("total_chunks", 0)
                    }
                    for doc in retrieved_docs
                ],
                "retrieval_count": len(retrieved_docs)
            }
            
            logger.info(f"RAG query processed successfully for question: {question[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process RAG query: {e}")
            return {
                "answer": "I apologize, but I encountered an error while processing your question. Please try again.",
                "sources": [],
                "retrieval_count": 0,
                "error": str(e)
            }
    
    def get_vector_store_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        try:
            # This would require implementing a method to count documents
            # For now, return basic info
            return {
                "status": "connected",
                "collection": "documents",
                "message": "Vector store is operational"
            }
        except Exception as e:
            logger.error(f"Failed to get vector store stats: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


# Global RAG pipeline instance
rag_pipeline = None


def get_rag_pipeline() -> RAGPipeline:
    """Get the global RAG pipeline instance."""
    global rag_pipeline
    if rag_pipeline is None:
        rag_pipeline = RAGPipeline()
    return rag_pipeline


def initialize_rag_pipeline() -> RAGPipeline:
    """Initialize the RAG pipeline."""
    return get_rag_pipeline()

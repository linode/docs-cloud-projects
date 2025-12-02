"""
LangGraph conversation memory implementation with PostgreSQL checkpointing.
Handles persistent conversation state across sessions and restarts.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.core.config import get_settings
from app.core.rag import get_rag_pipeline

logger = logging.getLogger(__name__)
settings = get_settings()


class ConversationState(TypedDict):
    """State schema for LangGraph conversation."""
    messages: List[BaseMessage]
    thread_id: str
    user_input: str
    rag_result: Optional[Dict[str, Any]]


class ConversationMemory:
    """Manages conversation state using LangGraph with PostgreSQL checkpointing."""
    
    def __init__(self):
        """Initialize the conversation memory system."""
        self.checkpointer = None
        self.graph = None
        self._checkpointer_context = None
        self._initialize_checkpointer()
        self._create_conversation_graph()
    
    def __del__(self):
        """Clean up resources when the object is destroyed."""
        if hasattr(self, '_checkpointer_context') and self._checkpointer_context:
            try:
                # Exit the context manager
                self._checkpointer_context.__exit__(None, None, None)
            except Exception:
                pass
    
    def _initialize_checkpointer(self):
        """Initialize PostgreSQL checkpointer for conversation state."""
        try:
            # Try PostgreSQL first
            try:
                logger.info("Attempting to initialize PostgreSQL checkpointer...")
                checkpointer_cm = PostgresSaver.from_conn_string(settings.state_db_url)
                
                # Handle context manager properly
                if hasattr(checkpointer_cm, '__enter__'):
                    self.checkpointer = checkpointer_cm.__enter__()
                    self._checkpointer_context = checkpointer_cm
                    
                    # Set up the database schema if needed
                    try:
                        # Try different setup methods
                        if hasattr(self.checkpointer, 'setup'):
                            logger.info("Calling checkpointer.setup()...")
                            self.checkpointer.setup()
                            logger.info("PostgreSQL checkpointer schema set up successfully")
                        elif hasattr(self.checkpointer, 'create_tables'):
                            logger.info("Calling checkpointer.create_tables()...")
                            self.checkpointer.create_tables()
                            logger.info("PostgreSQL checkpointer tables created successfully")
                        else:
                            logger.warning("No setup method found on checkpointer")
                    except Exception as setup_error:
                        logger.warning(f"Schema setup failed: {setup_error}")
                        # Try to manually create the schema
                        try:
                            logger.info("Attempting manual schema creation...")
                            self._create_checkpoint_schema()
                        except Exception as manual_error:
                            logger.error(f"Manual schema creation failed: {manual_error}")
                    
                    logger.info("PostgreSQL checkpointer initialized successfully")
                else:
                    self.checkpointer = checkpointer_cm
                    self._checkpointer_context = None
                    
                    # Set up the database schema if needed
                    try:
                        if hasattr(self.checkpointer, 'setup'):
                            self.checkpointer.setup()
                            logger.info("PostgreSQL checkpointer schema set up successfully")
                    except Exception as setup_error:
                        logger.warning(f"Schema setup failed (may already exist): {setup_error}")
                    
                    logger.info("PostgreSQL checkpointer initialized successfully")
                    
            except Exception as e:
                logger.warning(f"PostgreSQL checkpointer failed: {e}")
                logger.info("Falling back to MemorySaver...")
                self.checkpointer = MemorySaver()
                self._checkpointer_context = None
                logger.info("Memory checkpointer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize checkpointer: {e}")
            raise
    
    def _create_checkpoint_schema(self):
        """Manually create the checkpoint schema if automatic setup fails."""
        try:
            import psycopg2
            conn = psycopg2.connect(settings.state_db_url)
            cursor = conn.cursor()
            
            # Drop existing checkpoints table if it exists (with old schema)
            cursor.execute("DROP TABLE IF EXISTS checkpoints CASCADE;")
            
            # Create the checkpoints table with the correct schema for langgraph-checkpoint-postgres 1.0.0
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
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
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id ON checkpoints(thread_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_parent ON checkpoints(parent_checkpoint_id);")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("Manual checkpoint schema created successfully")
        except Exception as e:
            logger.error(f"Failed to create manual schema: {e}")
            raise
    
    def _create_conversation_graph(self):
        """Create the LangGraph conversation graph."""
        try:
            # Create the graph with state schema
            workflow = StateGraph(ConversationState)
            
            # Add nodes
            workflow.add_node("rag_query", self._rag_query_node)
            workflow.add_node("generate_response", self._generate_response_node)
            
            # Define the flow
            workflow.set_entry_point("rag_query")
            workflow.add_edge("rag_query", "generate_response")
            workflow.add_edge("generate_response", END)
            
            # Compile the graph with checkpointer
            self.graph = workflow.compile(checkpointer=self.checkpointer)
            
            logger.info("Conversation graph created successfully")
        except Exception as e:
            logger.error(f"Failed to create conversation graph: {e}")
            raise
    
    def _rag_query_node(self, state: ConversationState) -> ConversationState:
        """Node that processes RAG query."""
        try:
            rag_pipeline = get_rag_pipeline()
            
            # Build context from conversation history
            conversation_context = self._build_conversation_context(state["messages"])
            
            # Combine current question with conversation context
            contextual_question = self._build_contextual_question(state["user_input"], conversation_context)
            
            rag_result = rag_pipeline.query(contextual_question)
            
            state["rag_result"] = rag_result
            logger.debug(f"RAG query processed for thread {state['thread_id']}")
            return state
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            state["rag_result"] = {
                "answer": "I apologize, but I encountered an error while processing your question.",
                "sources": [],
                "retrieval_count": 0,
                "error": str(e)
            }
            return state
    
    def _build_conversation_context(self, messages: List[Dict[str, Any]], exclude_last_user_message: bool = True) -> str:
        """Build conversation context from message history."""
        if not messages:
            return ""
        
        context_parts = []
        # Get last 5 messages, but exclude the most recent user message if requested
        messages_to_use = messages[:-1] if exclude_last_user_message and messages and messages[-1]["type"] == "HumanMessage" else messages
        
        for msg in messages_to_use[-5:]:  # Last 5 messages for context
            if msg["type"] == "HumanMessage":
                context_parts.append(f"User: {msg['content']}")
            elif msg["type"] == "AIMessage":
                context_parts.append(f"Assistant: {msg['content']}")
        
        return "\n".join(context_parts)
    
    def _build_contextual_question(self, current_question: str, conversation_context: str) -> str:
        """Build a contextual question that includes conversation history."""
        if not conversation_context:
            return current_question
        
        return f"""Previous conversation context:
{conversation_context}

Current question: {current_question}

Please answer the current question considering the conversation context above. If the current question refers to something mentioned earlier (like "my previous question" or "what I asked before"), please use the conversation context to understand what they're referring to."""
    
    def _generate_response_node(self, state: ConversationState) -> ConversationState:
        """Node that generates the final response."""
        try:
            rag_result = state["rag_result"]
            answer = rag_result.get("answer", "I couldn't generate a response.")
            
            # Create AI message and convert to serializable format
            ai_message = AIMessage(content=answer)
            
            # Convert messages to serializable format for PostgreSQL storage
            serializable_messages = []
            for msg in state["messages"]:
                if isinstance(msg, dict):
                    # Already in serializable format
                    serializable_messages.append(msg)
                else:
                    # Convert LangChain message object to serializable format
                    serializable_messages.append({
                        "type": msg.__class__.__name__,
                        "content": msg.content,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # Add the new AI message
            serializable_messages.append({
                "type": "AIMessage",
                "content": answer,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            state["messages"] = serializable_messages
            
            logger.debug(f"Response generated for thread {state['thread_id']}")
            return state
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            # Add error message in serializable format
            error_message = {
                "type": "AIMessage",
                "content": "I apologize, but I encountered an error while generating a response.",
                "timestamp": datetime.utcnow().isoformat()
            }
            state["messages"].append(error_message)
            return state
    
    def process_message(self, message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user message and return the response.
        
        Args:
            message: The user's message
            thread_id: Optional thread ID for conversation continuity
            
        Returns:
            Dictionary with response and thread information
        """
        try:
            # Generate thread ID if not provided
            if not thread_id:
                thread_id = str(uuid.uuid4())
            
            # Get existing conversation history first
            existing_history = self.get_conversation_history(thread_id)
            existing_messages = existing_history.get("messages", [])
            
            # Create human message in serializable format
            human_message = {
                "type": "HumanMessage",
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Prepare initial state with existing messages + new message
            initial_state = {
                "messages": existing_messages + [human_message],
                "thread_id": thread_id,
                "user_input": message,
                "rag_result": None
            }
            
            # Configure the graph with thread ID
            config = {"configurable": {"thread_id": thread_id}}
            
            # Run the conversation graph
            final_state = self.graph.invoke(initial_state, config=config)
            
            # Extract the response
            messages = final_state["messages"]
            ai_response = messages[-1]["content"] if messages else "No response generated."
            
            result = {
                "response": ai_response,
                "thread_id": thread_id,
                "message_count": len(messages),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Message processed successfully for thread {thread_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return {
                "response": "I apologize, but I encountered an error while processing your message.",
                "thread_id": thread_id or str(uuid.uuid4()),
                "message_count": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    def get_conversation_history(self, thread_id: str) -> Dict[str, Any]:
        """
        Get conversation history for a thread.
        
        Args:
            thread_id: The conversation thread ID
            
        Returns:
            Dictionary with conversation history
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            # Get the current state
            state = self.graph.get_state(config)
            
            if not state.values:
                return {
                    "thread_id": thread_id,
                    "messages": [],
                    "created_at": None,
                    "updated_at": None,
                    "message_count": 0
                }
            
            # Extract messages
            messages = state.values.get("messages", [])
            
            # Messages are already in serializable format
            formatted_messages = messages if isinstance(messages, list) else []
            
            # Handle timestamps properly - check what attributes are available
            created_at = None
            updated_at = None
            
            # Check for created_at attribute
            if hasattr(state, 'created_at') and state.created_at:
                if hasattr(state.created_at, 'isoformat'):
                    created_at = state.created_at.isoformat()
                elif isinstance(state.created_at, str):
                    created_at = state.created_at
                    
            # Check for updated_at attribute (may not exist in all versions)
            if hasattr(state, 'updated_at') and state.updated_at:
                if hasattr(state.updated_at, 'isoformat'):
                    updated_at = state.updated_at.isoformat()
                elif isinstance(state.updated_at, str):
                    updated_at = state.updated_at
            else:
                # If updated_at doesn't exist, use created_at or current time
                updated_at = created_at
            
            result = {
                "thread_id": thread_id,
                "messages": formatted_messages,
                "created_at": created_at,
                "updated_at": updated_at,
                "message_count": len(formatted_messages)
            }
            
            logger.info(f"Retrieved conversation history for thread {thread_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return {
                "thread_id": thread_id,
                "messages": [],
                "created_at": None,
                "updated_at": None,
                "message_count": 0,
                "error": str(e)
            }
    
    def clear_conversation(self, thread_id: str) -> Dict[str, Any]:
        """
        Clear conversation history for a thread.
        
        Args:
            thread_id: The conversation thread ID
            
        Returns:
            Dictionary with operation result
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            # Update the state to clear messages
            self.graph.update_state(config, {"messages": []})
            
            result = {
                "success": True,
                "thread_id": thread_id,
                "message": "Conversation history cleared successfully"
            }
            
            logger.info(f"Cleared conversation history for thread {thread_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to clear conversation: {e}")
            return {
                "success": False,
                "thread_id": thread_id,
                "message": f"Failed to clear conversation: {str(e)}"
            }
    
    def get_checkpointer_stats(self) -> Dict[str, Any]:
        """Get statistics about the checkpointer."""
        try:
            # Check which type of checkpointer is being used
            checkpointer_type = "postgres" if isinstance(self.checkpointer, PostgresSaver) else "memory"
            
            if checkpointer_type == "postgres":
                return {
                    "status": "connected",
                    "type": "postgres",
                    "connection_string": settings.state_db_url.split('@')[1] if '@' in settings.state_db_url else "configured",
                    "message": "PostgreSQL checkpointer is operational"
                }
            else:
                return {
                    "status": "connected",
                    "type": "memory",
                    "message": "Memory checkpointer is operational (conversations will not persist across restarts)"
                }
        except Exception as e:
            logger.error(f"Failed to get checkpointer stats: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


# Global conversation memory instance
conversation_memory = None


def get_conversation_memory() -> ConversationMemory:
    """Get the global conversation memory instance."""
    global conversation_memory
    if conversation_memory is None:
        conversation_memory = ConversationMemory()
    return conversation_memory


def initialize_conversation_memory() -> ConversationMemory:
    """Initialize the conversation memory system."""
    return get_conversation_memory()
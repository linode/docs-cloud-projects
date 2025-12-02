"""
Chat API endpoints for the LangChain RAG Chatbot.
Handles conversation management and message processing.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.core.memory import get_conversation_memory
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    conversation_memory=Depends(get_conversation_memory)
) -> ChatResponse:
    """
    Process a chat message and return the AI response.
    
    Args:
        request: Chat request containing message and optional thread_id
        conversation_memory: Dependency injection for conversation memory
        
    Returns:
        ChatResponse with the AI's response and thread information
    """
    try:
        logger.info(f"Processing chat message: {request.message[:50]}...")
        
        # Process the message through the conversation memory system
        result = conversation_memory.process_message(
            message=request.message,
            thread_id=request.thread_id
        )
        
        # Create response
        response = ChatResponse(
            response=result["response"],
            thread_id=result["thread_id"]
        )
        
        logger.info(f"Chat message processed successfully for thread {result['thread_id']}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to process chat message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )


@router.get("/conversation/{thread_id}")
async def get_conversation_history(
    thread_id: str,
    conversation_memory=Depends(get_conversation_memory)
) -> Dict[str, Any]:
    """
    Get conversation history for a specific thread.
    
    Args:
        thread_id: The conversation thread ID
        conversation_memory: Dependency injection for conversation memory
        
    Returns:
        Dictionary with conversation history
    """
    try:
        logger.info(f"Retrieving conversation history for thread: {thread_id}")
        
        history = conversation_memory.get_conversation_history(thread_id)
        
        logger.info(f"Retrieved conversation history for thread {thread_id}")
        return history
        
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversation history: {str(e)}"
        )


@router.delete("/conversation/{thread_id}")
async def clear_conversation(
    thread_id: str,
    conversation_memory=Depends(get_conversation_memory)
) -> Dict[str, Any]:
    """
    Clear conversation history for a specific thread.
    
    Args:
        thread_id: The conversation thread ID
        conversation_memory: Dependency injection for conversation memory
        
    Returns:
        Dictionary with operation result
    """
    try:
        logger.info(f"Clearing conversation history for thread: {thread_id}")
        
        result = conversation_memory.clear_conversation(thread_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
        
        logger.info(f"Cleared conversation history for thread {thread_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear conversation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear conversation: {str(e)}"
        )



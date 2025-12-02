"""
Main FastAPI application for the LangChain RAG Chatbot.
Entry point for the application with all routes and middleware configured.
"""

import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn

from app.core.config import get_settings, validate_environment
from app.core.rag import initialize_rag_pipeline
from app.core.memory import initialize_conversation_memory
from app.api import chat, health

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting LangChain RAG Chatbot application")
    
    # Validate environment variables
    if not validate_environment():
        logger.error("Environment validation failed")
        raise RuntimeError("Missing required environment variables")
    
    # Initialize core components
    try:
        logger.info("Initializing RAG pipeline...")
        initialize_rag_pipeline()
        logger.info("RAG pipeline initialized successfully")
        
        logger.info("Initializing conversation memory...")
        initialize_conversation_memory()
        logger.info("Conversation memory initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application components: {e}")
        raise
    
    logger.info("Application startup completed successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LangChain RAG Chatbot application")


# Create FastAPI application
app = FastAPI(
    title="LangChain RAG Chatbot",
    description="A production-ready chatbot with RAG and persistent conversation memory",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "Invalid request data",
            "details": exc.errors()
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }
    )


# Include API routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(health.router, prefix="/api", tags=["health"])


# Serve static files
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main chat interface."""
    try:
        static_file_path = "app/static/index.html"
        if os.path.exists(static_file_path):
            with open(static_file_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        else:
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>LangChain RAG Chatbot</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .container { max-width: 800px; margin: 0 auto; }
                    h1 { color: #333; }
                    .status { background: #f0f8ff; padding: 20px; border-radius: 8px; margin: 20px 0; }
                    .endpoints { background: #f9f9f9; padding: 20px; border-radius: 8px; }
                    .endpoint { margin: 10px 0; }
                    code { background: #e8e8e8; padding: 2px 6px; border-radius: 4px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>LangChain RAG Chatbot</h1>
                    <div class="status">
                        <h2>Application Status</h2>
                        <p>Application is running successfully</p>
                        <p>RAG pipeline initialized</p>
                        <p>Conversation memory enabled</p>
                    </div>
                    <div class="endpoints">
                        <h2>Available Endpoints</h2>
                        <div class="endpoint">
                            <strong>POST</strong> <code>/api/chat</code> - Send a chat message
                        </div>
                        <div class="endpoint">
                            <strong>GET</strong> <code>/api/health</code> - Check application health
                        </div>
                        <div class="endpoint">
                            <strong>GET</strong> <code>/api/conversation/{thread_id}</code> - Get conversation history
                        </div>
                        <div class="endpoint">
                            <strong>DELETE</strong> <code>/api/conversation/{thread_id}</code> - Clear conversation history
                        </div>
                    </div>
                    <p><a href="/docs">View API Documentation</a></p>
                </div>
            </body>
            </html>
            """)
    except Exception as e:
        logger.error(f"Failed to serve root page: {e}")
        return HTMLResponse(content="<h1>Error loading page</h1>", status_code=500)


@app.get("/docs")
async def docs():
    """Redirect to FastAPI docs."""
    return {"message": "Visit /docs for API documentation"}


def main():
    """Main entry point for running the application."""
    logger.info(f"Starting server on {settings.app_host}:{settings.app_port}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,  # Set to True for development
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()

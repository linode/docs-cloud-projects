# LangChain RAG Chatbot

A production-ready chatbot that answers questions from your own documents using Retrieval-Augmented Generation (RAG) and maintains conversation memory across sessions.

## Features

- **RAG Pipeline**: Upload documents, get accurate answers based on your content
- **Persistent Conversations**: Chat history survives restarts and can be resumed anytime
- **Separated Databases**: Vector store and conversation state in isolated PostgreSQL instances
- **Object Storage**: Documents stored in Linode Object Storage for durability
- **Simple Interface**: Clean HTML/CSS/JS chat UI included
- **Production Ready**: systemd service, health checks, logging

## Architecture

```
┌─────────────────┐
│  FastAPI App    │
│   (Linode)      │
└────────┬────────┘
         │
    ┌────┴────┬─────────┬──────────────┐
    ↓         ↓         ↓              ↓
┌────────┐ ┌──────┐ ┌─────────┐ ┌──────────┐
│Vector  │ │State │ │ Object  │ │ OpenAI   │
│DB      │ │DB    │ │ Storage │ │ API      │
└────────┘ └──────┘ └─────────┘ └──────────┘
```

## Tech Stack

- **LangChain 0.2.16** + **LangGraph 0.2.16**: Orchestration and conversation state
- **PostgreSQL + pgvector**: Vector database for embeddings
- **PostgreSQL**: Separate database for conversation checkpoints (langgraph-checkpoint-postgres)
- **Linode Object Storage**: Document storage (S3-compatible)
- **OpenAI API**: LLM (gpt-4o-mini) and embeddings (text-embedding-3-small)
- **FastAPI + Uvicorn**: Web framework and ASGI server
- **Python 3.11+** (tested with Python 3.11)

## Prerequisites

- Linode account
- OpenAI API key
- Python 3.11 or higher (tested with Python 3.11)

## Quick Start

### 1. Clone this Repository

### 2. Set Up Infrastructure

**Create Linode Instance**
- Launch a Linode with 4GB+ RAM (8GB recommended)
- Ubuntu 22.04 LTS
- Configure firewall to allow SSH and port 8000

**Create PostgreSQL Databases**

Create two Managed PostgreSQL instances in Linode Cloud Manager:

1. **Vector Database** (for RAG embeddings)
   - Connect and enable pgvector: `CREATE EXTENSION vector;`
   
2. **State Database** (for conversation history)
   - No special extensions needed

Add your Linode's IP to the allowed list for both databases.

**Create Object Storage Bucket**

1. Create a bucket in Linode Object Storage
2. Generate access keys
3. Note your endpoint URL

### 3. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# OpenAI
OPENAI_API_KEY=sk-your-api-key-here

# PostgreSQL Databases
VECTOR_DB_URL=postgresql://user:pass@host:5432/vectordb
STATE_DB_URL=postgresql://user:pass@host:5432/statedb

# Linode Object Storage
LINODE_OBJECT_STORAGE_ACCESS_KEY=your-access-key
LINODE_OBJECT_STORAGE_SECRET_KEY=your-secret-key
LINODE_OBJECT_STORAGE_ENDPOINT=https://us-east-1.linodeobjects.com
LINODE_OBJECT_STORAGE_BUCKET=langchain-documents

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
```

### 5. Initialize Databases

```bash
python scripts/init_db.py
```

This creates necessary tables and indexes in both databases.

### 6. Index Documents

```bash
# Index all documents from your Linode Object Storage bucket
python scripts/index_documents.py
```

Documents are automatically chunked and embedded into the vector database. The script will process all files in your configured bucket.

### 7. Configure Firewall

```bash
sudo ufw allow 8000/tcp
sudo ufw enable
```


### 8. Run the Application

**Development**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production** (see DEPLOYMENT.md for systemd service setup):
```bash
sudo systemctl start langchain-chatbot
```

### 9. Access the Chat Interface

Open your browser to `http://your-linode-ip:8000`

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   ├── chat.py          # Chat endpoint
│   │   └── health.py        # Health check endpoint
│   ├── core/
│   │   ├── config.py        # Configuration management
│   │   ├── rag.py           # RAG pipeline implementation
│   │   └── memory.py        # LangGraph conversation memory
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   └── static/
│       └── index.html       # Chat interface
├── scripts/
│   ├── init_db.py           # Database initialization
│   └── index_documents.py   # Document upload and indexing
├── .env.example             # Example environment variables
├── requirements.txt         # Python dependencies
└── README.md
```

## Usage

### Chat API

**POST /api/chat**

```bash
curl -X POST http://your-linode-ip:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the refund policy?",
    "thread_id": "user-123"
  }'
```

Response:
```json
{
  "response": "According to our documentation, refunds are processed within 30 days...",
  "thread_id": "user-123",
  "message_count": 2,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Health Check

**GET /api/health**

```bash
curl http://your-linode-ip:8000/api/health
```

Response:
```json
{
  "status": "healthy",
  "vector_db": "connected",
  "state_db": "connected",
  "openai_api": "available",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Conversation Management

**GET /api/conversation/{thread_id}** - Retrieve conversation history
**DELETE /api/conversation/{thread_id}** - Clear conversation history
## Monitoring

### View Logs

```bash
# systemd logs
sudo journalctl -u langchain-chatbot -f

# Application logs
tail -f /var/log/langchain-chatbot.log
```

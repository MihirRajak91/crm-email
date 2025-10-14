CRM
Modern FastAPI service for RAG‑powered chat and status‑aware email composition grounded on company documents in Qdrant.

Features
- FastAPI app with modular routers and lifespan management
- Qdrant vector store integration and async embedding
- RAG chat (REST, WebSocket, SSE stream)
- Status‑aware email composer (new, contacted, qualified, lost)
- Centralized prompt templates and safe logging

Architecture
- API: `crm.main:app` with routers under `crm/routers`
- Retrieval: Qdrant client in `crm/utils/qdrand_db.py`
- Embeddings: Async embedder in `crm/utils/embedder.py`
- LLM: Provider‑select via `crm/services/llm_service.py` (OpenAI or Ollama)
- Email Composer: `crm/services/email_composer_service.py`
- Prompts: `crm/prompts/*.py`

Requirements
- Python 3.12+
- Poetry (dependency management)
- Docker (to run Qdrant locally)
- OpenAI API key if using OpenAI for LLM/embeddings

Quick Start
1) Install dependencies
   - poetry install
2) Start Qdrant (local)
   - sudo docker run -p 6333:6333 -v $(pwd)/qdrant_db:/qdrant/storage qdrant/qdrant
3) Configure environment (.env)
   - Copy `.env.example` to `.env` and adjust values (see “Configuration”)
4) Run the server
   - Dev: poetry run uvicorn crm.main:app --reload --env-file .env.dev
   - Staging: poetry run uvicorn crm.main:app --reload --env-file .env.staging
   - Prod: poetry run uvicorn crm.main:app --reload --env-file .env.prod

Configuration (env)
Core settings are defined in `crm/core/settings.py`. Common variables:
- ENV=dev|staging|prod
- DEBUG=true|false
- LLM_PROVIDER=openai|ollama
- OPENAI_API_KEY=... (required for OpenAI)
- OPENAI_LLM_MODEL=gpt-4o-mini (example)
- OPENAI_EMBEDDING_MODEL=text-embedding-3-small (example)
- QDRANT_HOST=localhost
- QDRANT_PORT=6333
- LOCAL_LLM_MODEL=llama3.1 (if using Ollama)
- LOCAL_EMBEDDING_MODEL=embed (if using local embeddings)
- LOCAL_COLLECTION_NAME=CRM_zeta_documents (used when ENV=dev)
- OPENAI_COLLECTION_NAME=CRM_zeta_documents_openai (used when ENV!=dev)

Email Composer
Composes sales emails grounded in your Qdrant docs. Retrieval is similarity‑only (no access filters).

- Endpoint: POST /api/email/compose
  - Request (ComposeEmailRequest):
    - status: new | contacted | qualified | lost
    - past_emails: array of `{ "subject": str | null, "body": str }` ordered oldest → newest
    - recipient_name, recipient_company: optional strings (light personalization)
    - top_k: integer (default 6)
  - Response (ComposeEmailResponse):
    - subject: string
    - body: string

Example
curl -X POST http://localhost:8000/api/email/compose \
  -H "Content-Type: application/json" \
  -d '{
        "status": "new",
        "past_emails": [
          {"subject": "Initial outreach", "body": "…"},
          {"subject": "Lead reply", "body": "…"}
        ],
        "recipient_name": "Riley",
        "recipient_company": "ExampleCo",
        "top_k": 6
      }'

Email Update (echo utility)
- Endpoint: POST /api/email/update
- Use when you need to validate payload shape; echoes inputs with safe logging.

How Retrieval Works
- Query hint is built from status + hints (product/persona/industry/tags)
- Embedded via async embedder and searched in Qdrant
- No access filters are applied (organization/role/user are ignored)
- Top‑k chunks’ `payload.text` are summarized into a compact digest used by prompts

Expected Qdrant Payload Fields
- Required: `text`
- Helpful: `title` or `file_name`, `resource_id`, `chunk_id`
- Optional tags: `doc_type`, `product`, `tags`

Prompts
- All templates live in `crm/prompts/email_prompts.py`:
  - CONTEXT_DIGEST_TEMPLATE — condense retrieved text
  - EMAIL_NEW_TEMPLATE, EMAIL_CONTACTED_TEMPLATE, EMAIL_QUALIFIED_TEMPLATE, EMAIL_LOST_TEMPLATE

Chat Endpoints (RAG)
- POST /api/chat — standard chat with history and retrieval
- POST /api/chat/stream — SSE streaming of token chunks to client
- WS /api/ws/chat — WebSocket chat

Running With Example WebSocket Client
See snippet below for connecting to `/ws/chat`.

Example ws/chat usage
import asyncio
import websockets
import json

async def chat_with_ai():
    uri = "ws://localhost:8000/ws/chat"
    async with websockets.connect(uri) as websocket:
        payload = {
            "query": "What is AI?",
            "organization_id": "12345",
            "user_id": "67890",
            "roles": ["admin"],
            "conversation_id": None,
            "include_history": False
        }
        await websocket.send(json.dumps(payload))
        response = await websocket.recv()
        print(f"Response from AI: {response}")

asyncio.run(chat_with_ai())

Troubleshooting
- Qdrant connection errors
  - Ensure Docker is running and port 6333 is free
  - Verify QDRANT_HOST/PORT in your .env
- OpenAI errors or generic outputs
  - Set OPENAI_API_KEY and select a valid model in .env
  - In dev (ENV=dev), embeddings default to local model unless you override
- Empty sources or generic emails
  - Make sure your documents are ingested with `payload.text` and helpful metadata

Testing
- Optional: install pytest and run tests
  - pip install pytest
  - pytest -q

License
MIT

# CRM Developer Documentation
## Complete Technical Guide & Onboarding

---

## 🎯 **System Overview**

CRM is a **Retrieval-Augmented Generation (RAG)** system built with FastAPI, Qdrant vector database, and multiple LLM providers. It provides intelligent document search and conversational AI capabilities.

### **Tech Stack**
- **Backend**: FastAPI (Python 3.12+)
- **Vector Database**: Qdrant
- **LLM Providers**: OpenAI, Ollama (with fallback)
- **Document Processing**: Unstructured, PyPDF, Docx2txt
- **Embeddings**: Sentence Transformers (Nomic AI)
- **Caching**: Redis
- **Message Queue**: RabbitMQ
- **Database**: MongoDB
- **Containerization**: Docker & Docker Compose

---

## 🏗️ **System Architecture**

### **High-Level Architecture**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   Qdrant        │
│   (Web/API)     │◄──►│   Backend       │◄──►│   Vector DB     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   LLM Service   │
                       │ (OpenAI/Ollama) │
                       └─────────────────┘
```

### **Core Components**

#### 1. **API Layer** (`crm/routers/`)
- **`response_generation_router.py`**: Main chat endpoints
- **`response_generation_router_optimized.py`**: High-performance chat
- **`auth.py`**: Authentication endpoints
- **`document_list_router.py`**: Document management
- **`evaluation_router.py`**: System evaluation tools

#### 2. **Service Layer** (`crm/services/`)
- **`qdrant_response.py`**: Core RAG logic
- **`qdrant_response_optimized.py`**: Async RAG implementation
- **`llm_service.py`**: Unified LLM provider management
- **`openai_services.py`**: OpenAI integration
- **`ollama_services.py`**: Ollama integration
- **`conversation_manager.py`**: Chat history management

#### 3. **Data Layer** (`crm/utils/`)
- **`qdrand_db.py`**: Qdrant client
- **`embedder.py`**: Text embedding generation
- **`mongodb_connection.py`**: MongoDB client
- **`rabbitmq_utils.py`**: Message queue utilities

#### 4. **Configuration** (`crm/configs/`)
- **`constant.py`**: System constants
- **`performance_config.py`**: Performance settings
- **`collection_name_configs.py`**: Database collection names

---

## 🔄 **Complete Code Flow**

### **1. Request Entry Point**

```python
# crm/routers/response_generation_router.py
@router.post('/chat')
async def chat(payload: ChatBot, current_user: User = Depends(get_current_user)):
    # 1. Validate payload
    # 2. Extract user info from JWT
    # 3. Call DocumentQAService
    response = document_obj.generate_answer(
        user_query=payload.query,
        organization_id=organization_id,
        user_id=user_id,
        user_roles=[role_id],
        conversation_id=payload.conversation_id,
        include_history=payload.include_history
    )
```

### **2. LLM Provider Selection**

```python
# crm/services/llm_service.py
def get_llm():
    provider = os.getenv('LLM_PROVIDER', LLM_PROVIDER).lower()
    
    if provider == 'openai':
        try:
            from crm.services.openai_services import openai_llm
            if hasattr(openai_llm, 'invoke'):
                return openai_llm  # ✅ OpenAI
            else:
                provider = 'ollama'  # ⚠️ Fallback
        except ImportError:
            provider = 'ollama'  # ⚠️ Fallback
    
    if provider == 'ollama':
        try:
            from crm.services.ollama_services import llm
            if hasattr(llm, 'invoke'):
                return llm  # ✅ Ollama
            else:
                return FallbackLLM()  # 📝 Static fallback
        except ImportError:
            return FallbackLLM()  # 📝 Static fallback
```

### **3. Document Processing Flow**

```python
# crm/services/qdrant_response.py
def generate_answer(self, user_query, organization_id, user_id, user_roles, conversation_id):
    
    # Step 1: Parallel Processing
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(create_chat_history): "history",
            executor.submit(self.generate_embedding, user_query): "embedding"
        }
    
    # Step 2: Vector Search
    results = self.client.search(
        collection_name=self.collection_name,
        query_vector=query_vector,
        limit=top_k,
        query_filter=search_filter,
        score_threshold=score_threshold
    )
    
    # Step 3: Cache Check
    doc_fingerprint = self.generate_doc_fingerprint(results)
    cached_response = self.chat_cache.get_conversation(...)
    if cached_response:
        return cached_response  # ✅ Cache hit
    
    # Step 4: Context Preparation
    context = "\n".join(hit.payload.get("text", "") for hit in results)
    
    # Step 5: LLM Invocation
    answer = self.chain.invoke({
        "conversation_context": conversation_context,
        "context": context,
        "question": user_query
    })
    
    # Step 6: Cache Storage
    self.chat_cache.set_conversation(...)
    
    # Step 7: Response Formatting
    return {
        "answer": answer,
        "conversation_id": conversation_id,
        "results": formatted_results,
        "performance": metrics.to_dict(),
        "knowledge_request": knowledge_request
    }
```

### **4. LLM Invocation Details**

```python
# The chain is defined as:
self.chain = prompt_template | llm

# Which translates to:
llm.invoke(prompt_template.format(
    conversation_context=conversation_context,
    context=context,
    question=user_query
))
```

---

## 📁 **Project Structure**

```
crm/
├── crm/
│   ├── routers/                    # API endpoints
│   │   ├── response_generation_router.py
│   │   ├── response_generation_router_optimized.py
│   │   ├── auth.py
│   │   ├── document_list_router.py
│   │   └── evaluation_router.py
│   ├── services/                   # Business logic
│   │   ├── qdrant_response.py
│   │   ├── qdrant_response_optimized.py
│   │   ├── llm_service.py
│   │   ├── openai_services.py
│   │   ├── ollama_services.py
│   │   └── conversation_manager.py
│   ├── utils/                      # Utilities
│   │   ├── embedder.py
│   │   ├── qdrand_db.py
│   │   ├── mongodb_connection.py
│   │   └── rabbitmq_utils.py
│   ├── configs/                    # Configuration
│   │   ├── constant.py
│   │   ├── performance_config.py
│   │   └── collection_name_configs.py
│   ├── models/                     # Data models
│   │   ├── process_request.py
│   │   ├── auth_models.py
│   │   └── upload_resource_model.py
│   ├── cache/                      # Caching
│   │   └── chat_cache.py
│   ├── rabbitmq/                   # Message queue
│   │   ├── consumers.py
│   │   └── producers.py
│   └── dependencies/               # FastAPI dependencies
│       └── auth.py
├── tests/                          # Test files
├── logs/                           # Application logs
├── docker-compose.yml              # Docker configuration
├── pyproject.toml                  # Poetry configuration
└── server.py                       # Application entry point
```

---

## 🚀 **Quick Start Guide**

### **1. Environment Setup**

```bash
# Clone the repository
git clone <repository-url>
cd crm

# Install dependencies
poetry install

# Copy environment file
cp env.example .env

# Edit .env with your configuration
nano .env
```

### **2. Environment Configuration**

```bash
# Required environment variables
LLM_PROVIDER=openai                    # or 'ollama'
OPENAI_API_KEY=your_openai_key        # OpenAI API key
OPENAI_MODEL=gpt-3.5-turbo            # Model to use

# Database configuration
MONGODB_HOST=localhost
REDIS_HOST=localhost
QDANT_HOST=localhost

# Optional: Ollama fallback
LLAMA3_API_KEY=http://localhost:11434
```

### **3. Start Services**

```bash
# Start with Docker Compose
docker-compose up -d

# Or start individual services
# MongoDB, Redis, Qdrant, RabbitMQ
```

### **4. Run the Application**

```bash
# Development mode
poetry run python server.py

# Or with uvicorn
poetry run uvicorn server:app --reload
```

---

## 🔧 **Development Workflow**

### **1. Understanding the Codebase**

#### **Start with these files:**
1. **`server.py`**: Application entry point
2. **`crm/routers/response_generation_router.py`**: Main API endpoints
3. **`crm/services/qdrant_response.py`**: Core RAG logic
4. **`crm/services/llm_service.py`**: LLM provider management

#### **Key Concepts to Understand:**
- **RAG Pattern**: Retrieve → Augment → Generate
- **Vector Search**: Semantic similarity search
- **LLM Fallback**: Multiple AI providers
- **Async Processing**: Performance optimization
- **Caching Strategy**: Redis-based response caching

### **2. Adding New Features**

#### **New API Endpoint:**
```python
# crm/routers/your_router.py
from fastapi import APIRouter
from crm.services.your_service import YourService

router = APIRouter()
service = YourService()

@router.post('/your-endpoint')
async def your_endpoint(payload: YourModel):
    return service.process(payload)
```

#### **New Service:**
```python
# crm/services/your_service.py
from crm.utils.logger import logger

class YourService:
    def __init__(self):
        self.logger = logger
    
    def process(self, payload):
        # Your business logic here
        return {"result": "success"}
```

### **3. Testing**

```bash
# Run tests
poetry run python -m pytest tests/

# Run specific test
poetry run python -m pytest tests/test_title_decision.py

# Run with coverage
poetry run python -m pytest --cov=crm tests/
```

---

## 🔍 **Debugging Guide**

### **1. Logging**

```python
# crm/utils/logger.py
from crm.utils.logger import logger

logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.debug("Debug message")
```

### **2. Common Issues**

#### **LLM Connection Issues:**
```bash
# Check OpenAI API key
echo $OPENAI_API_KEY

# Test OpenAI connection
python test_llm_integration.py

# Check Ollama service
curl http://localhost:11434/api/tags
```

#### **Database Connection Issues:**
```bash
# Check MongoDB
mongo --host localhost --port 27017

# Check Redis
redis-cli ping

# Check Qdrant
curl http://localhost:6333/collections
```

#### **Performance Issues:**
```python
# Enable performance metrics
from crm.services.qdrant_response import DocumentQAService

service = DocumentQAService()
response = service.generate_answer(...)
print(response["performance"])  # Check timing metrics
```

### **3. Monitoring**

#### **Application Metrics:**
- **Response Time**: Check `performance` field in responses
- **Cache Hit Rate**: Monitor Redis cache statistics
- **LLM Usage**: Track API calls to OpenAI/Ollama
- **Error Rates**: Monitor application logs

#### **System Metrics:**
- **CPU Usage**: Monitor during high load
- **Memory Usage**: Check for memory leaks
- **Disk I/O**: Monitor database performance
- **Network**: Check API response times

---

## 📚 **Key Components Deep Dive**

### **1. Document Processing Pipeline**

```python
# crm/services/add_file_services.py
class AddFileServices:
    def process_file(self, file_path, metadata):
        # 1. Extract text from document
        text = self.extract_text(file_path)
        
        # 2. Split into chunks
        chunks = self.split_text(text)
        
        # 3. Generate embeddings
        embeddings = self.embedder.encode(chunks)
        
        # 4. Store in Qdrant
        self.store_in_qdrant(chunks, embeddings, metadata)
```

### **2. Vector Search Implementation**

```python
# crm/services/qdrant_response.py
def search_documents(self, query_vector, filter_conditions):
    results = self.client.search(
        collection_name=self.collection_name,
        query_vector=query_vector,
        limit=top_k,
        query_filter=filter_conditions,
        score_threshold=score_threshold
    )
    return results
```

### **3. LLM Integration**

```python
# crm/services/llm_service.py
def get_llm():
    provider = os.getenv('LLM_PROVIDER', 'openai')
    
    if provider == 'openai':
        return ChatOpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
            temperature=0.1
        )
    elif provider == 'ollama':
        return OllamaLLM(
            base_url=os.getenv('LLAMA3_API_KEY'),
            model=os.getenv('LLAMA_MODEL', 'llama3.1')
        )
```

### **4. Caching Strategy**

```python
# crm/cache/chat_cache.py
class ChatCache:
    def get_conversation(self, query, org_id, user_id, roles, fingerprint):
        cache_key = self.generate_cache_key(query, org_id, user_id, roles, fingerprint)
        return self.redis_client.get(cache_key)
    
    def set_conversation(self, query, org_id, user_id, roles, fingerprint, response):
        cache_key = self.generate_cache_key(query, org_id, user_id, roles, fingerprint)
        self.redis_client.setex(cache_key, 3600, json.dumps(response))  # 1 hour TTL
```

---

## 🔄 **API Reference**

### **Main Endpoints**

#### **Chat Endpoints:**
- `POST /chat`: Standard chat with conversation context
- `POST /chat/optimized`: High-performance async chat
- `POST /chat/batch`: Batch processing for multiple queries
- `WebSocket /ws/chat`: Real-time chat interface

#### **Document Management:**
- `GET /documents`: List documents by organization
- `POST /upload`: Upload new documents
- `DELETE /documents/{id}`: Delete documents

#### **Authentication:**
- `GET /token`: Get JWT access token
- `GET /user-info`: Get current user information

#### **Evaluation:**
- `POST /evaluate/single`: Evaluate single query
- `POST /evaluate/batch`: Batch evaluation
- `GET /evaluate/metrics/average`: Get average metrics

### **Request/Response Models**

```python
# Chat Request
class ChatBot(BaseModel):
    query: str
    conversation_id: str
    include_history: bool = True
    user_id: Optional[str] = None
    organization_id: Optional[str] = None

# Chat Response
{
    "answer": str,
    "conversation_id": str,
    "has_context": bool,
    "context": str,
    "results": List[DocumentResult],
    "performance": PerformanceMetrics,
    "total_results": int,
    "knowledge_request": bool
}
```

---

## 🧪 **Testing Strategy**

### **1. Unit Tests**

```python
# tests/test_qdrant_response.py
def test_generate_answer():
    service = DocumentQAService()
    response = service.generate_answer(
        user_query="What is the capital of France?",
        organization_id="test-org",
        user_id="test-user",
        user_roles=["admin"],
        conversation_id="test-conv"
    )
    assert response["answer"] is not None
    assert "conversation_id" in response
```

### **2. Integration Tests**

```python
# tests/test_live_response.py
def test_chat_endpoint():
    client = TestClient(app)
    response = client.post("/chat", json={
        "query": "What is the capital of France?",
        "conversation_id": "test-conv"
    })
    assert response.status_code == 200
    assert "answer" in response.json()
```

### **3. Performance Tests**

```python
# tests/test_performance.py
def test_batch_processing():
    service = OptimizedDocumentQAService()
    queries = ["query1", "query2", "query3"]
    results = await service.batch_generate_answers(queries)
    assert len(results) == len(queries)
```

---

## 🚀 **Deployment Guide**

### **1. Docker Deployment**

```bash
# Build and run with Docker Compose
docker-compose up -d

# Check services
docker-compose ps

# View logs
docker-compose logs -f
```

### **2. Production Configuration**

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  app:
    build: .
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    ports:
      - "8000:8000"
    depends_on:
      - mongodb
      - redis
      - qdrant
```

### **3. Environment Variables**

```bash
# Production environment variables
ENVIRONMENT=production
LOG_LEVEL=INFO
OPENAI_API_KEY=your_production_key
MONGODB_HOST=your_mongodb_host
REDIS_HOST=your_redis_host
QRANT_HOST=your_qdrant_host
```

---

## 📈 **Performance Optimization**

### **1. Async Processing**

```python
# Use async endpoints for better performance
@router.post('/chat/optimized')
async def chat_optimized(payload: ChatBot):
    return await optimized_service.generate_answer_async(payload)
```

### **2. Caching Strategy**

```python
# Implement caching at multiple levels
# 1. Response caching
# 2. Embedding caching
# 3. Document caching
```

### **3. Database Optimization**

```python
# Use connection pooling
# Implement read replicas
# Optimize indexes
```

---

## 🔒 **Security Considerations**

### **1. Authentication**

```python
# JWT-based authentication
@router.post('/chat')
async def chat(payload: ChatBot, current_user: User = Depends(get_current_user)):
    # Validate user permissions
    # Check organization access
    # Verify role permissions
```

### **2. Data Protection**

```python
# Encrypt sensitive data
# Implement access controls
# Audit logging
```

### **3. API Security**

```python
# Rate limiting
# Input validation
# CORS configuration
```

---

## 📞 **Getting Help**

### **1. Documentation Resources**
- **API Documentation**: `/docs` (Swagger UI)
- **Code Documentation**: Inline docstrings
- **Architecture Diagrams**: See system overview

### **2. Debugging Tools**
- **Logging**: Comprehensive logging system
- **Metrics**: Performance monitoring
- **Testing**: Automated test suite

### **3. Community Support**
- **GitHub Issues**: Bug reports and feature requests
- **Code Reviews**: Peer review process
- **Documentation**: Keep docs updated

---

*This documentation provides a comprehensive guide for developers joining the CRM project. For business stakeholders, please refer to the Stakeholder Documentation.* 

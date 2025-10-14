"""
Description: Configuration constants for the CRM system including exchange names, events, messages, and thresholds

args:
    None (module-level constants)

returns:
    Various constant values for system configuration
"""

EXCHANGE_NAME = 'embedder_exchange'

RABBITMQ_CONSUMER_QUEUES = [
    "create_embedding",
    "batch_embedding",
    "edit_embedding",
    "delete_embedding",
    "embedding_results",
    "event_response",
]

EVENTS = [
    "create_embedding",
    "batch_embedding",
    "edit_embedding",
    "delete_embedding",
    "embedding_response",
    "event_response",
]
UPDATE_PERMISSION_EVENT = "update_permissions"
DELETE_EVENT="delete_resource"
NO_DOCUMENTS_MESSAGE = "Sorry, I don't have access to documents related to this topic. You can add a new document if you'd like me to help with that."
OLLAMA_FALLBACK_MESSAGE = "⚠️ The LLM service is currently unavailable. Please try again later."
# Default similarity threshold for document retrieval (0.0 to 1.0)
DEFAULT_SIMILARITY_THRESHOLD = 0.6

# LLM Provider Configuration

# Set this to 'openai' or 'ollama' to switch between providers
LLM_PROVIDER = 'ollama'  # Change this to switch between 'openai' and 'ollama'

# OpenAI Configuration
OPENAI_API_KEY = None  # Set via environment variable OPENAI_API_KEY
OPENAI_MODEL = 'gpt-3.5-turbo'  # Default OpenAI model
OPENAI_TIMEOUT = 30  # Timeout in seconds
OPENAI_MAX_TOKENS = 2000  # Maximum tokens for response

# Ollama Configuration (existing)
OLLAMA_API_KEY = None  # Set via environment variable LLAMA3_API_KEY
OLLAMA_MODEL = 'llama3.1'  # Default Ollama model
OLLAMA_TIMEOUT = 5  # Timeout in seconds

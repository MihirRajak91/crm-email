import os
from dotenv import load_dotenv
from crm.utils.logger import logger
from crm.configs.constant import LLM_PROVIDER, OLLAMA_FALLBACK_MESSAGE
from crm.core.settings import get_settings

load_dotenv()

class FallbackLLM:
    """Wrapper class to make fallback function compatible with LangChain LLM interface"""
    
    def __init__(self):
        self.fallback_message = OLLAMA_FALLBACK_MESSAGE
    
    def invoke(self, prompt: str) -> str:
        """Invoke method that returns the fallback message"""
        logger.warning("⚠️ Fallback LLM in use. Returning static response.")
        return self.fallback_message

def get_llm():  
    """
    Description: Get the appropriate LLM based on the LLM_PROVIDER configuration
    
    args:
        None (uses LLM_PROVIDER constant and environment variables)
    
    returns:
        LLM instance: Either OpenAI or Ollama LLM based on configuration
    """
    settings = get_settings()
    if not settings.LLM_PROVIDER:
        logger.error("LLM_PROVIDER is not set in the configuration. Using fallback.")
        return FallbackLLM()
    provider = settings.LLM_PROVIDER
    logger.info(f"Loading LLM provider: {provider}")
    
    if provider == 'openai':
        try:
            from crm.services.openai_services import openai_llm
            # Check if openai_llm is a proper LLM instance or fallback function
            if hasattr(openai_llm, 'invoke'):
                logger.info("Using OpenAI LLM")
                return openai_llm
            else:
                logger.warning("OpenAI failed, falling back to Ollama")
                provider = 'ollama'
        except ImportError as e:
            logger.error(f"Failed to import OpenAI service: {e}")
            logger.warning("Falling back to Ollama")
            provider = 'ollama'
    
    if provider == 'ollama':
        try:
            from crm.services.ollama_services import llm
            # Check if ollama_llm is a proper LLM instance or fallback function
            if hasattr(llm, 'invoke'):
                logger.info("Using Ollama LLM")
                return llm
            else:
                logger.warning("Ollama failed, using fallback")
        except ImportError as e:
            logger.error(f"Failed to import Ollama service: {e}")
    
    # Fallback to a proper LLM wrapper
    logger.error("No LLM provider available, using fallback")
    return FallbackLLM()

# Initialize the LLM based on configuration
llm = get_llm() 
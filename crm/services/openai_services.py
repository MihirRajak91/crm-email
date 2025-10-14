import os
# from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from crm.utils.logger import logger
from crm.configs.constant import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TIMEOUT, OPENAI_MAX_TOKENS, OLLAMA_FALLBACK_MESSAGE
from crm.core.settings import get_settings

settings = get_settings()
# load_dotenv()

def load_openai_llm():
    """
    Description: Load and initialize OpenAI LLM with environment configuration and fallback handling
    
    args:
        None (uses environment variables OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TIMEOUT)
    
    returns:
        ChatOpenAI or fallback_llm: Configured LLM instance or fallback function on failure
    """
    api_key = settings.OPENAI_API_KEY
    model_name = settings.OPENAI_LLM_MODEL
    # api_key = os.getenv('OPENAI_API_KEY', OPENAI_API_KEY)
    # model_name = os.getenv('OPENAI_MODEL', OPENAI_MODEL)
    timeout = OPENAI_TIMEOUT
    max_tokens = OPENAI_MAX_TOKENS
    
    if api_key:
        logger.info(f"OpenAI API KEY: {api_key[:10]}... and model name {model_name}")
    else:
        logger.info(f"OpenAI API KEY: Not set, model name {model_name}")

    if not api_key:
        logger.error("OPENAI_API_KEY is not set.")
        return fallback_llm

    try:
        logger.info(f"Connecting to OpenAI using model {model_name} ...")
        llm = ChatOpenAI(
            api_key=api_key,
            model=model_name,
            timeout=timeout,
            max_tokens=max_tokens,
            temperature=0.1  # Low temperature for consistent responses
        )

        return llm
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI LLM: {e}")

    return fallback_llm

def fallback_llm(prompt: str) -> str:
    """
    Description: Fallback LLM function that returns static response when main LLM fails
    
    args:
        prompt (str): Input prompt (ignored in fallback)
    
    returns:
        str: Static fallback message from configuration
    """
    logger.warning("Fallback LLM in use. Returning static response.")
    return OLLAMA_FALLBACK_MESSAGE

# Initialize OpenAI LLM
openai_llm = load_openai_llm() 
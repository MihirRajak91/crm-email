import os
from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from crm.utils.logger import logger
import httpx
from crm.configs.constant import OLLAMA_FALLBACK_MESSAGE
from typing import Iterator, AsyncGenerator
import json
from crm.core.settings import get_settings

settings = get_settings()
# load_dotenv()

OLLAMA_BASE_URL = settings.OLLAMA_API_URL
OLLAMA_TIMEOUT  = int(os.getenv("OLLAMA_TIMEOUT", 5))
OLLAMA_MODEL    = settings.LOCAL_LLM_MODEL

# OLLAMA_BASE_URL = os.getenv("LLAMA3_API_KEY", "http://localhost:11434")
# OLLAMA_TIMEOUT  = int(os.getenv("OLLAMA_TIMEOUT", 5))
# OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",   "llama3.1")

def load_llm():
    api_key = OLLAMA_BASE_URL
    model_name = OLLAMA_MODEL
    # model_name = os.getenv('LLAMA_MODEL', MODEL_NAME)
    # timeout = int(os.getenv("OLLAMA_TIMEOUT", 5))    
    logger.info(f"API KEY :  {api_key} ... and model name {model_name}")

# ----------------------------------------------------------------------
# Thin wrapper around Ollama (no LangChain)
# ----------------------------------------------------------------------
class DirectOllama:
    def __init__(self, base_url: str, model: str, timeout: int):
        self.base_url = base_url.rstrip("/")
        self.model    = model
        self.timeout  = timeout

    # ---------- blocking, non-streaming ----------
    def invoke(self, prompt: str) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        r = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        )
        r.raise_for_status()
        return json.loads(r.text)["response"]

    # ---------- streaming ----------
    def stream(self, prompt: str) -> Iterator[str]:
        payload = {"model": self.model, "prompt": prompt, "stream": True}
        with httpx.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if "response" in chunk:
                    logger.info(f"Received chunk: {chunk['response'][:60]}...")
                    yield chunk["response"]

    # ---------- async streaming ----------
    async def astream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Async generator that yields tokens as they arrive."""
        payload = {"model": self.model, "prompt": prompt, "stream": True}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if "response" in chunk:
                        yield chunk["response"]

# ----------------------------------------------------------------------
# Low-level helpers
# ----------------------------------------------------------------------
def _ping_ollama() -> bool:
    try:
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=OLLAMA_TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False
    

def load_llm():
    """
    Description: Load and initialize Ollama LLM with environment configuration and fallback handling
    
    args:
        None (uses environment variables LLAMA3_API_KEY, LLAMA_MODEL, OLLAMA_TIMEOUT)
    
    returns:
        OllamaLLM or fallback_llm: Configured LLM instance or fallback function on failure
    """
    if not _ping_ollama():
        logger.error("Ollama server not reachable.")
        return fallback_llm

    try:
        logger.info(f"Connecting to Ollama at {OLLAMA_BASE_URL} using model {OLLAMA_MODEL} ...")
        llm = DirectOllama(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            timeout=OLLAMA_TIMEOUT
        )
        test_response = llm.invoke("Hello, who are you?")
        logger.info(f"Ollama responded: {test_response[:60]}...")
        return llm
    except httpx.ConnectTimeout:
        logger.error(f"Connection to Ollama timed out after {OLLAMA_TIMEOUT} seconds.")
    except Exception as e:
        logger.error(f"Failed to initialize OllamaLLM: {e}")

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

# Initialize the LLM instance
llm = load_llm()


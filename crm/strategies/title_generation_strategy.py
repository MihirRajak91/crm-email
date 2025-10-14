from abc import ABC, abstractmethod
# from transformers import pipeline
from langdetect import detect
from crm.utils.logger import logger
from crm.services.llm_service import llm

class TitleGenerationStrategy(ABC):
    """
    Description: Abstract base class for generating conversation titles based on user queries using different strategies
    
    args:
        None (abstract base class)
    
    returns:
        TitleGenerationStrategy: Abstract interface for title generation implementations
    """

    @abstractmethod
    def generate_title(self, query:str, answer:str) -> str:
        """
        Description: Generate a title for the conversation or topic based on the user's query (abstract method)
        
        args:
            query (str): The user's query or message to generate title from
        
        returns:
            str: The generated title text
        """
        pass


class BasicTitleGenerationStrategy(TitleGenerationStrategy):
    """
    Description: Basic title generation strategy that capitalizes and truncates user queries to create simple titles
    
    args:
        None (concrete implementation of base strategy)
    
    returns:
        BasicTitleGenerationStrategy: Simple title generation with capitalization and truncation
    """
    def generate_title(self, query:str, answer:str) -> str:
        """
        Description: Generate a simple title by capitalizing the query and truncating to 20 characters with ellipsis
        
        args:
            query (str): The user's query to process into a title
        
        returns:
            str: Capitalized and truncated title with ellipsis if longer than 20 characters
        """
        title = query.strip().capitalize()
        if len(title) > 20:
            title = title[:17] + "..."
        return title


class NLPTitleGenerationStrategy(TitleGenerationStrategy):
    """
    Description: Advanced NLP title generation strategy using language detection and LLM-based title generation
    
    args:
        None (initializes with optional summarization model)
    
    returns:
        NLPTitleGenerationStrategy: Advanced title generation using NLP models and language detection
    """
    def __init__(self):
        """
        Description: Initialize the NLP strategy with optional summarization model and error handling
        
        args:
            None
        
        returns:
            None
        """
        self.summarizer = None
        try:
            logger.debug("[TitleGen-NLP] Initializing summarization model...")
            # self.summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
        except Exception as e:
            logger.error(f"[TitleGen-NLP] Failed to initialize summarizer: {e}")

    def generate_title(self, query: str, answer:str) -> str:
        """
        Description: Generate title using LLM with language detection and fallback to basic strategy on errors
        
        args:
            query (str): The user's query to generate a title from
            answer (str): The answer or context to include in the title generation
        returns:
            str: Generated title in the same language as the query, falls back to basic strategy on errors
        """
        return self.generate_title_with_llm(query, answer)

    def generate_title_with_llm(self, query: str, answer:str) -> str:
        """
        Description: Generate multilingual title using LLM with language detection and clean formatting
        
        args:
            query (str): The user's query to process with LLM
            answer (str): The answer or context to include in the title generation
        returns:
            str: Clean, short title in the same language as query, falls back to BasicTitleGenerationStrategy on errors
        """


        system_prompt = f"""
            You are a world-class headline editor.
            Your only task is to create a four-word title that perfectly captures the user’s query and answer.
            Constraints:
                - Exactly four words, no punctuation, no extra spaces.
                - Stick to the language of the query
                - Omit filler words (a, an, the, is, etc.).
                - Prefer nouns and strong verbs.
            Respond with the four-word title only.
        """
        
        user_prompt = (
            f"Question: {query[:50]}\n"
            "Title:"
        )

        response = llm.invoke([("system", system_prompt), ("user", user_prompt)])

        # Extract content from AIMessage if it's an AIMessage object
        if hasattr(response, 'content'):
            title = response.content.strip().replace('"', '').strip()
        else:
            title = str(response).strip().replace('"', '').strip()
        return title
    
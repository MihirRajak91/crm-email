from dataclasses import dataclass
from datetime import datetime

@dataclass
class PerformanceMetrics:
    """
    Description: Dataclass for tracking performance metrics of document QA operations with timing and conversation data
    
    args:
        query (str): The user query that was processed
        timestamp (datetime): Timestamp when the operation started
        embedding_time (float): Time taken for text embedding in seconds
        search_time (float): Time taken for vector search in seconds
        llm_time (float): Time taken for LLM response generation in seconds
        total_time (float): Total operation time in seconds
        conversation_history_time (float): Time taken to retrieve conversation history in seconds
        results_count (int): Number of document results retrieved
        conversation_id (str): Unique identifier for the conversation
    
    returns:
        PerformanceMetrics: Instance containing detailed timing and operation metrics
    """
    query: str
    timestamp: datetime
    embedding_time: float
    search_time: float
    llm_time: float
    total_time: float
    conversation_history_time: float
    results_count: int
    conversation_id: str

    def to_dict(self) -> dict:
        """
        Description: Convert performance metrics to dictionary format for serialization and logging
        
        args:
            None (method of the instance)
        
        returns:
            dict: Dictionary containing all performance metrics with rounded float values
        """
        return {
            "query": self.query,
            "timestamp": self.timestamp.isoformat(),
            "embedding_time": round(self.embedding_time, 3),
            "search_time": round(self.search_time, 3),
            "llm_time": round(self.llm_time, 3),
            "total_time": round(self.total_time, 3),
            "conversation_history_time": round(self.conversation_history_time, 3),
            "results_count": self.results_count,
            "conversation_id": self.conversation_id
        }


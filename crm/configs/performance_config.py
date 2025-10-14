import os
import multiprocessing
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class PerformanceConfig:
    """
    Description: Configuration dataclass for performance and parallelization settings across the CRM system
    
    args:
        max_file_workers (int): Maximum worker threads for file processing, defaults to 4
        max_embedding_workers (int): Maximum workers for embedding generation, defaults to 2
        max_db_workers (int): Maximum workers for database operations, defaults to 4
        max_rabbitmq_workers (int): Maximum workers for RabbitMQ message processing, defaults to 4
        embedding_batch_size (int): Batch size for embedding operations, defaults to 32
        db_batch_size (int): Batch size for database operations, defaults to 100
        file_batch_size (int): Batch size for file processing, defaults to 10
        message_queue_size (int): Size of message queues, defaults to 100
        prefetch_count (int): RabbitMQ prefetch count, defaults to 4
        embedding_timeout (int): Timeout for embedding operations in seconds, defaults to 300
        file_processing_timeout (int): Timeout for file processing in seconds, defaults to 600
        db_operation_timeout (int): Timeout for database operations in seconds, defaults to 60
        max_retries (int): Maximum retry attempts, defaults to 3
        retry_delay (float): Delay between retries in seconds, defaults to 1.0
        max_memory_usage_mb (int): Maximum memory usage in MB, defaults to 2048
        chunk_size (int): Text chunk size for processing, defaults to 500
        chunk_overlap (int): Overlap between text chunks, defaults to 100
        video_conversion_workers (int): Workers for video conversion, defaults to 2
        video_batch_size (int): Batch size for video processing, defaults to 5
    
    returns:
        PerformanceConfig: Configuration instance with performance settings
    """
    
    # Worker thread/process configuration
    max_file_workers: int = 4
    max_embedding_workers: int = 2
    max_db_workers: int = 4
    max_rabbitmq_workers: int = 4
    
    # Batch processing configuration
    embedding_batch_size: int = 32
    db_batch_size: int = 100
    file_batch_size: int = 10
    
    # Queue and buffer sizes
    message_queue_size: int = 100
    prefetch_count: int = 4
    
    # Timeout settings (in seconds)
    embedding_timeout: int = 300
    file_processing_timeout: int = 600
    db_operation_timeout: int = 60
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Memory management
    max_memory_usage_mb: int = 2048
    chunk_size: int = 500  # Characters (legacy for docs)
    chunk_overlap: int = 100  # Characters (legacy for docs)
    
    # Token-based chunking (optimized for your use case)
    max_tokens_per_chunk: int = 1000  # Optimal for text-embedding-3-small
    token_overlap: int = 200  # 20% overlap (industry best practice)
    
    # Video-specific settings (for transcripts)
    video_max_tokens: int = 800      # Optimal for speech patterns  
    video_token_overlap: int = 160   # 20% overlap for video content
    
    # Local embedding settings (for nomic-ai model)
    local_max_tokens: int = 2048     # Optimal for nomic-embed-text-v1.5
    local_token_overlap: int = 410   # 20% overlap for local model
    
    # Video processing
    video_conversion_workers: int = 2
    video_batch_size: int = 5
    
    @classmethod
    def from_env(cls) -> 'PerformanceConfig':
        """
        Description: Load configuration from environment variables with CPU-aware defaults
        
        args:
            None (uses environment variables and CPU count for intelligent defaults)
        
        returns:
            PerformanceConfig: Configuration instance populated from environment variables
        """
        cpu_count = multiprocessing.cpu_count()
        
        return cls(
            max_file_workers=int(os.getenv('MAX_FILE_WORKERS', min(cpu_count, 4))),
            max_embedding_workers=int(os.getenv('MAX_EMBEDDING_WORKERS', min(cpu_count // 2, 2))),
            max_db_workers=int(os.getenv('MAX_DB_WORKERS', min(cpu_count, 4))),
            max_rabbitmq_workers=int(os.getenv('MAX_RABBITMQ_WORKERS', min(cpu_count, 4))),
            
            embedding_batch_size=int(os.getenv('EMBEDDING_BATCH_SIZE', 32)),
            db_batch_size=int(os.getenv('DB_BATCH_SIZE', 100)),
            file_batch_size=int(os.getenv('FILE_BATCH_SIZE', 10)),
            
            message_queue_size=int(os.getenv('MESSAGE_QUEUE_SIZE', 100)),
            prefetch_count=int(os.getenv('PREFETCH_COUNT', 4)),
            
            embedding_timeout=int(os.getenv('EMBEDDING_TIMEOUT', 300)),
            file_processing_timeout=int(os.getenv('FILE_PROCESSING_TIMEOUT', 600)),
            db_operation_timeout=int(os.getenv('DB_OPERATION_TIMEOUT', 60)),
            
            max_retries=int(os.getenv('MAX_RETRIES', 3)),
            retry_delay=float(os.getenv('RETRY_DELAY', 1.0)),
            
            max_memory_usage_mb=int(os.getenv('MAX_MEMORY_USAGE_MB', 2048)),
            chunk_size=int(os.getenv('CHUNK_SIZE', 500)),
            chunk_overlap=int(os.getenv('CHUNK_OVERLAP', 100)),
            max_tokens_per_chunk=int(os.getenv('MAX_TOKENS_PER_CHUNK', 1000)),
            token_overlap=int(os.getenv('TOKEN_OVERLAP', 200)),
            video_max_tokens=int(os.getenv('VIDEO_MAX_TOKENS', 800)),
            video_token_overlap=int(os.getenv('VIDEO_TOKEN_OVERLAP', 160)),
            local_max_tokens=int(os.getenv('LOCAL_MAX_TOKENS', 2048)),
            local_token_overlap=int(os.getenv('LOCAL_TOKEN_OVERLAP', 410)),
            
            video_conversion_workers=int(os.getenv('VIDEO_CONVERSION_WORKERS', 2)),
            video_batch_size=int(os.getenv('VIDEO_BATCH_SIZE', 5)),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Description: Convert configuration instance to dictionary format for serialization
        
        args:
            None
        
        returns:
            Dict[str, Any]: Dictionary representation of all configuration values
        """
        return {
            'max_file_workers': self.max_file_workers,
            'max_embedding_workers': self.max_embedding_workers,
            'max_db_workers': self.max_db_workers,
            'max_rabbitmq_workers': self.max_rabbitmq_workers,
            'embedding_batch_size': self.embedding_batch_size,
            'db_batch_size': self.db_batch_size,
            'file_batch_size': self.file_batch_size,
            'message_queue_size': self.message_queue_size,
            'prefetch_count': self.prefetch_count,
            'embedding_timeout': self.embedding_timeout,
            'file_processing_timeout': self.file_processing_timeout,
            'db_operation_timeout': self.db_operation_timeout,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'max_memory_usage_mb': self.max_memory_usage_mb,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'max_tokens_per_chunk': self.max_tokens_per_chunk,
            'token_overlap': self.token_overlap,
            'video_max_tokens': self.video_max_tokens,
            'video_token_overlap': self.video_token_overlap,
            'local_max_tokens': self.local_max_tokens,
            'local_token_overlap': self.local_token_overlap,
            'video_conversion_workers': self.video_conversion_workers,
            'video_batch_size': self.video_batch_size,
        }

# Global configuration instance
perf_config = PerformanceConfig.from_env()

def get_optimal_workers(task_type: str) -> int:
    """
    Description: Get optimal number of workers for a specific task type based on configuration
    
    args:
        task_type (str): Type of task ('file_processing', 'embedding', 'database', 'messaging', 'video')
    
    returns:
        int: Optimal number of workers for the specified task type, defaults to 2 for unknown types
    """
    if task_type == 'file_processing':
        return perf_config.max_file_workers
    elif task_type == 'embedding':
        return perf_config.max_embedding_workers
    elif task_type == 'database':
        return perf_config.max_db_workers
    elif task_type == 'messaging':
        return perf_config.max_rabbitmq_workers
    elif task_type == 'video':
        return perf_config.video_conversion_workers
    else:
        return 2  # Conservative default

def get_optimal_batch_size(task_type: str) -> int:
    """
    Description: Get optimal batch size for a specific task type based on configuration
    
    args:
        task_type (str): Type of task ('embedding', 'database', 'file_processing', 'video')
    
    returns:
        int: Optimal batch size for the specified task type, defaults to 10 for unknown types
    """
    if task_type == 'embedding':
        return perf_config.embedding_batch_size
    elif task_type == 'database':
        return perf_config.db_batch_size
    elif task_type == 'file_processing':
        return perf_config.file_batch_size
    elif task_type == 'video':
        return perf_config.video_batch_size
    else:
        return 10  # Conservative default 

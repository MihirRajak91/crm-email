import os
import redis
# from dotenv import load_dotenv
from crm.utils.logger import logger
from crm.core.settings import get_settings

settings = get_settings()
# load_dotenv()

class RedisService:
    """
    Description: Service class for managing Redis connections with environment-based configuration
    
    args:
        None (initialized with empty client, connects on demand)
    
    returns:
        RedisService: Instance for managing Redis database connections
    """
    def __init__(self):
        """
        Description: Initialize the Redis service with empty client for lazy connection
        
        args:
            None
        
        returns:
            None
        """
        self.client = None

    def connect(self):
        """
        Description: Establish connection to Redis using environment variables with authentication support
        
        args:
            None (uses environment variables REDIS_HOST, REDIS_PORT_NUMBER, REDIS_PASSWORD)
        
        returns:
            redis.Redis: Connected Redis client instance with decode_responses enabled
        """
        try:
            redis_host = settings.REDIS_HOST
            redis_port = settings.REDIS_PORT
            redis_password = settings.REDIS_PASSWORD
            # redis_host = os.getenv("REDIS_HOST", "localhost")
            # redis_port = int(os.getenv("REDIS_PORT_NUMBER", 6379))
            # # redis_port = int(os.getenv("REDIS_PORT", 6379))
            # redis_password = os.getenv("REDIS_PASSWORD", None)

            self.client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True
            )
            self.client.ping()
            logger.info("Connected to Redis")
            return self.client
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    def get_redis_client(self):
        """
        Description: Get Redis client instance, connecting if not already connected
        
        args:
            None
        
        returns:
            redis.Redis: Redis client instance ready for operations
        """
        if self.client is None:
            return self.connect()
        return self.client

redis_service = RedisService()
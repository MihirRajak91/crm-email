import pika
import os
from dotenv import load_dotenv
from crm.configs.constant import EXCHANGE_NAME
from crm.core.settings import get_settings
from crm.utils.logger import logger

settings = get_settings()
# # Load the environment variables from .env file
# load_dotenv()

class RabbitMQConnection:
    """
    Description: RabbitMQ connection manager with environment-based configuration and connection lifecycle management
    
    args:
        connection_name (str): Name identifier for the connection, defaults to RABBITMQ_EXCHANGE_NAME or EXCHANGE_NAME
    
    returns:
        RabbitMQConnection: Instance for managing RabbitMQ connections with automatic retry and state tracking
    """
    def __init__(self, connection_name =os.getenv("RABBITMQ_EXCHANGE_NAME", EXCHANGE_NAME)):
        """
        Description: Initialize RabbitMQ connection manager with connection name and state tracking
        
        args:
            connection_name (str): Identifier for this connection instance
        
        returns:
            None
        """
        self.connection_name = connection_name
        self.connection = None
        self.is_initialized = False

    def initialize(self):
        """
        Description: Initialize RabbitMQ connection using environment variables with credentials and connection parameters
        
        args:
            None (uses environment variables RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_HOST, RABBITMQ_PORT)
        
        returns:
            None: Establishes connection and sets initialization status, prints debug information
        """
        if self.is_initialized and self.connection and not self.connection.is_closed:
            return
        try:
            user = settings.RABBITMQ_USER
            password = settings.RABBITMQ_PASSWORD
            host = settings.RABBITMQ_HOST
            port = settings.RABBITMQ_PORT
            # user = os.getenv("RABBITMQ_USER")
            # password = os.getenv("RABBITMQ_PASSWORD")
            # host = os.getenv("RABBITMQ_HOST")
            # port = os.getenv("RABBITMQ_PORT", "5672")

            # Debug print to verify environment variable values
            logger.debug(f"[DEBUG:{self.connection_name}] USER={user}, PASSWORD={password}, HOST={host}, PORT={port}")

            credentials = pika.PlainCredentials(user, password)
            parameters = pika.ConnectionParameters(
                host=host, 
                port=int(port),
                credentials=credentials
            )
            self.connection = pika.BlockingConnection(parameters)
            self.is_initialized = True
            logger.info(f" [x] RabbitMQ connection initialized ({self.connection_name})")
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ connection ({self.connection_name}): {e}")
            self.is_initialized = False
            self.connection = None

    def get_connection(self):
        """
        Description: Get active RabbitMQ connection with automatic reinitialization if connection is closed or unavailable
        
        args:
            None
        
        returns:
            pika.BlockingConnection: Active RabbitMQ connection, reinitializes if needed
        """
        if not self.is_initialized or not self.connection or self.connection.is_closed:
            logger.info(f"Connection not available ({self.connection_name}), attempting to reinitialize...")
            self.initialize()
        return self.connection

    def close(self):
        """
        Description: Close RabbitMQ connection gracefully and reset connection state with error handling
        
        args:
            None
        
        returns:
            None: Closes connection, resets state, prints status messages
        """
        if self.connection and not self.connection.is_closed:
            try:
                self.connection.close()
                logger.error(f" [x] RabbitMQ connection closed ({self.connection_name})")
            except Exception as e:
                logger.error(f"Failed to close RabbitMQ connection ({self.connection_name}): {e}")
            finally:
                self.is_initialized = False
                self.connection = None
                
                
rabbitmq_connection = RabbitMQConnection()

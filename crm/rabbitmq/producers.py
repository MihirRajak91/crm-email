import json
import pika
from .rabbitmq import RabbitMQConnection
from crm.utils.logger import logger

class RabbitMQProducer:
    """
    Description: RabbitMQ message producer with channel management and automatic reconnection for publishing messages
    
    args:
        exchange_name (str): Name of the RabbitMQ exchange to publish messages to
    
    returns:
        RabbitMQProducer: Instance for publishing messages to RabbitMQ with error handling and reconnection
    """
    def __init__(self, exchange_name):
        """
        Description: Initialize RabbitMQ producer with connection manager and exchange configuration
        
        args:
            exchange_name (str): Name of the exchange for message publishing
        
        returns:
            None
        """
        self.connection_manager = RabbitMQConnection("producer")
        self.connection_manager.initialize()
        self.channel = None
        self.exchange_name = exchange_name

    def get_channel(self):
        """
        Description: Get or create RabbitMQ channel with exchange declaration and error handling
        
        args:
            None
        
        returns:
            pika.channel.Channel: Active channel for message publishing, None if initialization fails
        """
        if self.channel is None or self.channel.is_closed:
            try:
                connection = self.connection_manager.get_connection()
                if not connection:
                    return None
                self.channel = connection.channel()
                self.channel.exchange_declare(exchange=self.exchange_name, exchange_type="direct", durable=True)
            except Exception as e:
                logger.error(f"Failed to initialize channel: {e}")
                self.channel = None
                return None
        return self.channel

    def _summarize_message(self, message):
        if not isinstance(message, dict):
            return message
        summary = {k: v for k, v in message.items() if k not in ("texts", "chunks", "embeddings")}
        texts = message.get("texts")
        if isinstance(texts, list):
            summary["texts_count"] = len(texts)
            if texts:
                first_chunk = texts[0] or ""
                words = first_chunk.split()
                summary["texts_preview"] = " ".join(words[:50])
        embeddings = message.get("embeddings")
        if isinstance(embeddings, list):
            summary["embeddings_count"] = len(embeddings)
            if embeddings:
                first_embedding = embeddings[0]
                if isinstance(first_embedding, list):
                    summary["embeddings_preview"] = first_embedding[:8]
                else:
                    summary["embeddings_preview"] = first_embedding
        return summary

    def publish_message(self, message, routing_key):
        """
        Description: Publish JSON message to exchange with routing key and automatic reconnection on failure
        
        args:
            message: Message object to serialize and publish
            routing_key (str): Routing key for message delivery
        
        returns:
            None: Publishes message with durable delivery, handles reconnection on errors
        """
        channel = self.get_channel()
        if channel is None:
            logger.info(f"Cannot publish to exchange {self.exchange_name}: channel unavailable")
            return
        try:
            channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2),
            )
            summary = self._summarize_message(message)
            logger.info(
                "Published message to exchange %s with routing key %s: %s",
                self.exchange_name,
                routing_key,
                summary,
            )
        except Exception as e:
            logger.error(f"Failed to send message to {self.exchange_name}: {e}")
            self.channel = None
            self.connection_manager.close()
            self.connection_manager.initialize()

    def close(self):
        """
        Description: Close producer channel and connection manager with graceful error handling
        
        args:
            None
        
        returns:
            None: Closes channel and connection, resets state
        """
        if self.channel and not self.channel.is_closed:
            try:
                self.channel.close()
                logger.info(f"Closed producer channel for exchange: {self.exchange_name}")
            except Exception as e:
                logger.error(f"Failed to close channel: {e}")
        self.channel = None
        self.connection_manager.close()

def rabbitmq_producer(message, exchange_name, routing_key, queue_name=None):
    """
    Description: Utility function to create producer and publish single message with automatic cleanup
    
    args:
        message: Message object to publish
        exchange_name (str): Name of the RabbitMQ exchange
        routing_key (str): Routing key for message delivery
        queue_name (str): Optional queue name parameter (not currently used)
    
    returns:
        None: Creates producer instance and publishes message
    """
    producer = RabbitMQProducer(exchange_name)
    event_name = message.get("event") if isinstance(message, dict) else None
    logger.info(
        f"Producing RabbitMQ event '{event_name or 'unknown'}' -> exchange {exchange_name}, routing {routing_key}"
    )
    producer.publish_message(message, routing_key)


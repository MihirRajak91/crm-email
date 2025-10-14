import pika
import json
import threading
import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from crm.rabbitmq.rabbitmq import RabbitMQConnection
from crm.services.event_processing import EventProcessor
from crm.configs.constant import EXCHANGE_NAME, EVENTS

logger = logging.getLogger(__name__)

class RabbitMQConsumer:
    """
    Description: Multi-threaded RabbitMQ consumer with async support for processing messages from multiple queues concurrently
    
    args:
        exchange_name (str): Name of the RabbitMQ exchange to consume from
        max_workers (int): Maximum number of worker threads for parallel processing, defaults to 4
    
    returns:
        RabbitMQConsumer: Instance for consuming and processing messages from RabbitMQ queues with event handling
    """
    def __init__(self, exchange_name, max_workers: int = 4):
        """
        Description: Initialize RabbitMQ consumer with threading support and event processor for parallel message handling
        
        args:
            exchange_name (str): Name of the RabbitMQ exchange for message consumption
            max_workers (int): Maximum number of concurrent worker threads for processing
        
        returns:
            None
        """
        self.threads = []
        self.running = False
        self.connection_managers = {}
        self.channels = {}
        self.exchange_name = exchange_name
        self.max_workers = max_workers
        self.file_processor = EventProcessor(max_workers=max_workers)

        # Async support
        self.loop = None
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.message_queue = asyncio.Queue(maxsize=100)

    def callback(self, ch, method, properties, body, queue_name):
        """
        Description: Message callback handler with JSON parsing, validation, and event routing with acknowledgment
        
        args:
            ch: RabbitMQ channel instance
            method: Message delivery method with delivery tag
            properties: Message properties from RabbitMQ
            body: Raw message body bytes
            queue_name (str): Name of the queue the message came from
        
        returns:
            None: Processes message and sends acknowledgment or negative acknowledgment
        """
        try:
            message = json.loads(body)
            logger.info(f"[RabbitMQ] Received message from '{queue_name}': {json.dumps(message, indent=2)}")

            # # Handle new nested payload structure
            # if isinstance(message, dict) and "payload" in message:
            #     payload = message["payload"]
            #     if isinstance(payload, dict) and "event" in payload:
            #         event = payload["event"]
            #         logger.info(f"[→] Handling event '{event}' via `process_message`")
            #         self.file_processor.process_message(payload)
            #         ch.basic_ack(delivery_tag=method.delivery_tag)
            #         return
            #     else:
            #         logger.warning(f"[!] Invalid payload structure from {queue_name}")
            #         ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            #         return

            # # Handle legacy format for backward compatibility
            # if not isinstance(message, dict) or "payload" not in message or "event" not in message["payload"]:
            #     logger.warning(f"[!] Invalid message format from {queue_name}")
            #     ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            #     return

            if isinstance(message, dict) and "event" not in message:
                logger.warning(f"[!] Invalid message form at from {queue_name} and message : {message}")
                logger.error("event name not found in message")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            # payload = message["payload"]
            payload = message
            text_preview = None
            texts_count = None
            embeddings_preview = None
            embeddings_count = None
            texts_field = payload.get("texts") if isinstance(payload, dict) else None
            if isinstance(texts_field, list):
                texts_count = len(texts_field)
                if texts_field:
                    first_chunk = texts_field[0] or ""
                    words = first_chunk.split()
                    text_preview = " ".join(words[:50])
            embeddings_field = payload.get("embeddings") if isinstance(payload, dict) else None
            if isinstance(embeddings_field, list):
                embeddings_count = len(embeddings_field)
                if embeddings_field:
                    first_embedding = embeddings_field[0]
                    if isinstance(first_embedding, list):
                        embeddings_preview = first_embedding[:8]
                    else:
                        embeddings_preview = first_embedding
            logger.info(
                "[RabbitMQ] Payload received: event=%s, resource=%s, texts=%s, text_preview=%s, embeddings_count=%s, embeddings_preview=%s",
                payload.get("event"),
                payload.get("resource_id"),
                texts_count,
                text_preview,
                embeddings_count,
                embeddings_preview,
            )
            event = payload["event"]

            if event in EVENTS:
                logger.info(f"[→] Handling event '{event}' via `process_message`")
                self.file_processor.process_message(payload)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                logger.info(f"[→] Event '{event}' not in EVENTS, falling back to `_process_message_sync`")
                self._process_message_sync(payload, ch, method)

        except json.JSONDecodeError:
            logger.error(f"[✖] Invalid JSON in message from {queue_name}: {body}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            logger.error(f"[!!] Error processing message from {queue_name}: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _process_message_sync(self, message, ch, method):
        """
        Description: Synchronous fallback message processor for events not in main EVENTS list with error handling
        
        args:
            message (dict): Parsed message payload containing event information
            ch: RabbitMQ channel for acknowledgments
            method: Message delivery method with delivery tag
        
        returns:
            None: Processes message synchronously and sends appropriate acknowledgment
        """
        try:
            event = message.get("event")

            if event in ("create_resource", "upload_resource", "edit_resource"):
                logger.info(f"[→] Handling event '{event}' via `handle_create_resource`")
                self.file_processor.process_message(message)
                ch.basic_ack(delivery_tag=method.delivery_tag)

            elif event == "delete_resource":
                logger.info(f"[→] Handling event '{event}' via `handle_delete_resource`")
                self.file_processor.process_message(message)
                ch.basic_ack(delivery_tag=method.delivery_tag)

            else:
                logger.warning(f"[~] Unknown event type '{event}'")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            logger.error(f"[!!] Error in sync processing: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def consume_queue(self, queue_name):
        """
        Description: Setup and start consuming from a specific queue with connection management and channel configuration
        
        args:
            queue_name (str): Name of the RabbitMQ queue to consume messages from
        
        returns:
            None: Runs continuously consuming messages until stopped, handles connection errors
        """
        connection_manager = RabbitMQConnection(f"consumer_{queue_name}")
        self.connection_managers[queue_name] = connection_manager

        # Retry loop to establish connection and start consuming
        while self.running:
            try:
                connection_manager.initialize()
                connection = connection_manager.get_connection()
                if not connection:
                    logger.error(f"Cannot consume from {queue_name}: connection unavailable; retrying in 5s")
                    time.sleep(5)
                    continue

                channel = connection.channel()
                channel.exchange_declare(exchange=self.exchange_name, exchange_type="direct", durable=True)
                channel.queue_declare(queue=queue_name, durable=True)
                channel.queue_bind(exchange=self.exchange_name, queue=queue_name, routing_key=queue_name)

                channel.basic_qos(prefetch_count=self.max_workers)
                channel.basic_consume(
                    queue=queue_name,
                    on_message_callback=lambda ch, method, properties, body: self.callback(ch, method, properties, body, queue_name)
                )
                self.channels[queue_name] = channel
                logger.info(f" [x] Started consuming from queue: {queue_name}")
                channel.start_consuming()
            except Exception as e:
                logger.error(f"Failed to consume from {queue_name}: {e!r}")
                self.channels.pop(queue_name, None)
                connection_manager.close()
                # Backoff before retry
                time.sleep(5)
            else:
                # If start_consuming returns (e.g., stop_consuming called), loop to reconnect
                time.sleep(1)

    def start(self, queue_names):
        """
        Description: Start consumer threads for multiple queues with parallel processing support
        
        args:
            queue_names (List[str]): List of queue names to start consuming from
        
        returns:
            None: Creates daemon threads for each queue and manages consumer state
        """
        logger.debug(f"Starting RabbitMQ consumer for queues : {queue_names}")
        if self.running:
            return
        self.running = True

        for queue_name in queue_names:
            thread = threading.Thread(target=self.consume_queue, args=(queue_name,), daemon=True)
            thread.start()
            self.threads.append(thread)
            logger.info(f" [x] Started consumer thread for queue: {queue_name}")

    def stop(self):
        """
        Description: Gracefully stop all consumer threads and close connections with proper cleanup
        
        args:
            None
        
        returns:
            None: Stops consuming, closes channels and connections, resets state
        """
        if not self.running:
            return
        self.running = False

        for queue_name, channel in list(self.channels.items()):
            if channel and not channel.is_closed:
                try:
                    channel.stop_consuming()
                    channel.close()
                    logger.info(f" [x] Stopped consuming from queue: {queue_name}")
                except Exception as e:
                    logger.error(f" [x] Error stopping consumer for {queue_name}: {e}")
            self.channels.pop(queue_name, None)
        for queue_name, conn in self.connection_managers.items():
            conn.close()
        self.connection_managers = {}


rabbitmq_consumer = RabbitMQConsumer(exchange_name=EXCHANGE_NAME)

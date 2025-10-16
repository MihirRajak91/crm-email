from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List

import pika

from crm.configs.constant import CRM_CHAT_REQUEST_QUEUE
from crm.models.email_models import ComposeEmailRequest, EmailThreadMessage, StatusEnum
from crm.rabbitmq.rabbitmq import RabbitMQConnection
from crm.services.email_composer_service import EmailComposerService
from crm.metrics import chat_failures_total, chat_processing_seconds

logger = logging.getLogger(__name__)


class ChatQueueWorker:
    """Consumes CRM chat/email requests and responds with composed emails."""

    def __init__(self) -> None:
        self._exchange = os.getenv("CRM_CHAT_EXCHANGE", "service_bus")
        self._request_queue = os.getenv("CRM_CHAT_REQUEST_QUEUE", CRM_CHAT_REQUEST_QUEUE)
        self._connection_manager = RabbitMQConnection("crm_chat_worker")
        self._service = EmailComposerService()
        self._channel: pika.adapters.blocking_connection.BlockingChannel | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> threading.Thread:
        if self._thread and self._thread.is_alive():
            return self._thread
        self._thread = threading.Thread(target=self._run, name="crm-chat-worker", daemon=True)
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        if self._channel and self._channel.is_open:
            try:
                self._channel.stop_consuming()
            except Exception:  # pragma: no cover
                pass
        self._connection_manager.close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _run(self) -> None:
        self._connection_manager.initialize()
        connection = self._connection_manager.get_connection()
        if not connection:
            logger.error("CRM chat worker could not acquire RabbitMQ connection")
            return

        channel = connection.channel()
        self._channel = channel

        channel.exchange_declare(exchange=self._exchange, exchange_type="direct", durable=True)
        channel.queue_declare(queue=self._request_queue, durable=True)
        channel.queue_bind(exchange=self._exchange, queue=self._request_queue, routing_key=self._request_queue)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=self._request_queue, on_message_callback=self._on_message)

        logger.info("CRM chat worker consuming queue %s on exchange %s", self._request_queue, self._exchange)
        try:
            channel.start_consuming()
        except Exception as exc:  # pragma: no cover
            logger.error("CRM chat worker stopped consuming: %s", exc)
        finally:
            self._channel = None
            self._connection_manager.close()

    def _on_message(self, ch, method, properties, body) -> None:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.error("CRM chat worker received invalid JSON: %s", body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        logger.debug("CRM chat worker payload: %s", payload)

        start = time.perf_counter()
        try:
            response = self._compose_email(payload)
        except Exception as exc:  # pragma: no cover - resilience
            chat_failures_total.labels(reason=exc.__class__.__name__).inc()
            logger.exception("CRM chat worker failed to compose email: %s", exc)
            response = {
                "reply": "I wasn't able to draft that email just now.",
                "metadata": {"error": str(exc)},
            }
        else:
            chat_processing_seconds.observe(time.perf_counter() - start)

        self._publish_response(ch, properties, response)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def _publish_response(self, channel, properties, response: Dict[str, Any]) -> None:
        reply_to = getattr(properties, "reply_to", None)
        correlation_id = getattr(properties, "correlation_id", None)
        if not reply_to:
            logger.error("CRM chat worker missing reply_to; dropping response: %s", response)
            return

        channel.basic_publish(
            exchange="",
            routing_key=reply_to,
            body=json.dumps(response).encode("utf-8"),
            properties=pika.BasicProperties(correlation_id=correlation_id),
        )

    def _compose_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        query = payload.get("query", "")
        history = payload.get("history") or []
        lead_data = payload.get("lead_data") or {}

        thread_messages: List[EmailThreadMessage] = []
        assembled = []
        for item in history[-5:]:
            role = item.get("role")
            content = item.get("content")
            if content:
                assembled.append(f"{role}: {content}")
        if query:
            assembled.append(f"user: {query}")
        if assembled:
            thread_messages.append(EmailThreadMessage(body="\n".join(assembled)))

        try:
            status = StatusEnum(lead_data.get("status", "new"))
        except ValueError:
            status = StatusEnum.NEW

        compose_request = ComposeEmailRequest(
            status=status,
            past_emails=thread_messages,
            recipient_name=lead_data.get("name"),
            recipient_company=lead_data.get("company") or payload.get("context", {}).get("org_id"),
        )

        async def _run() -> Dict[str, Any]:
            response = await self._service.compose(compose_request)
            return response.model_dump()

        result = asyncio.run(_run())
        reply_text = result.get("body") or "Here is a draft email for you."
        return {
            "reply": reply_text,
            "metadata": {
                "subject": result.get("subject"),
                "status": status.value,
            },
        }


def start_chat_worker() -> ChatQueueWorker:
    worker = ChatQueueWorker()
    worker.start()
    return worker

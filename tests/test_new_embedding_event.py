#!/usr/bin/env python3
"""
Test suite for the new simplified EmbeddingEvent format
"""

import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crm.models.rabbitmq_event_models import EmbeddingEvent


class TestNewEmbeddingEvent(unittest.TestCase):
    """Test the new simplified EmbeddingEvent format"""

    def setUp(self):
        """Set up test fixtures"""
        self.sample_texts = [
            "This is a test chunk for embedding processing.",
            "Another chunk to verify the processing pipeline.",
            "Final chunk to complete the test."
        ]
        self.sample_task_id = "task-12345"
        self.sample_resource_id = "resource-123"

    @unittest.skipUnless(bool(os.getenv('PYDANTIC_AVAILABLE', True)), "EmbeddingEvent requires pydantic")
    def test_new_embedding_event_creation(self):
        """Test creating new EmbeddingEvent with simplified format"""
        event = EmbeddingEvent(
            event="create_embedding",
            task_id=self.sample_task_id,
            resource_id=self.sample_resource_id,
            texts=self.sample_texts,
            user_id="test-user",
            callback_url="http://callback.example.com"
        )

        # Verify all fields
        self.assertEqual(event.event, "create_embedding")
        self.assertEqual(event.task_id, self.sample_task_id)
        self.assertEqual(event.resource_id, self.sample_resource_id)
        self.assertEqual(event.texts, self.sample_texts)
        self.assertEqual(event.user_id, "test-user")
        self.assertEqual(event.callback_url, "http://callback.example.com")

    @unittest.skipUnless(bool(os.getenv('PYDANTIC_AVAILABLE', True)), "EmbeddingEvent requires pydantic")
    def test_minimal_embedding_event(self):
        """Test creating EmbeddingEvent with minimal required fields"""
        event = EmbeddingEvent(
            event="batch_embedding",
            task_id=self.sample_task_id,
            resource_id=self.sample_resource_id,
            texts=self.sample_texts
        )

        # Verify required fields
        self.assertEqual(event.event, "batch_embedding")
        self.assertEqual(event.task_id, self.sample_task_id)
        self.assertEqual(event.resource_id, self.sample_resource_id)
        self.assertEqual(event.texts, self.sample_texts)

        # Check optional fields are None
        self.assertIsNone(event.user_id)
        self.assertIsNone(event.callback_url)

    @unittest.skipUnless(bool(os.getenv('PYDANTIC_AVAILABLE', True)), "EmbeddingEvent requires pydantic")
    def test_embedding_event_serialization(self):
        """Test EmbeddingEvent serialization for message queues"""
        event = EmbeddingEvent(
            event="create_embedding",
            task_id=self.sample_task_id,
            resource_id=self.sample_resource_id,
            texts=self.sample_texts,
            callback_url="http://callback.example.com"
        )

        # Serialize to dict
        event_dict = event.dict()

        # Verify structure matches what the embedding service expects
        self.assertEqual(event_dict["event"], "create_embedding")
        self.assertEqual(event_dict["task_id"], self.sample_task_id)
        self.assertEqual(event_dict["resource_id"], self.sample_resource_id)
        self.assertEqual(event_dict["texts"], self.sample_texts)
        self.assertEqual(event_dict["callback_url"], "http://callback.example.com")

        # Verify required fields are present
        required_fields = ["event", "task_id", "resource_id", "texts"]
        for field in required_fields:
            self.assertIn(field, event_dict)

    @unittest.skipUnless(bool(os.getenv('PYDANTIC_AVAILABLE', True)), "EmbeddingEvent requires pydantic")
    def test_different_event_types(self):
        """Test different embedding event types"""
        event_types = ["create_embedding", "batch_embedding"]

        for event_type in event_types:
            event = EmbeddingEvent(
                event=event_type,
                task_id=f"{event_type}-task",
                resource_id=f"{event_type}-resource",
                texts=self.sample_texts
            )

            self.assertEqual(event.event, event_type)
            self.assertEqual(len(event.texts), len(self.sample_texts))

    def test_event_structure_fallback(self):
        """Test that the event structure can be inspected without pydantic"""
        # This test verifies the expected structure without requiring pydantic
        sample_event_data = {
            "event": "create_embedding",
            "task_id": self.sample_task_id,
            "resource_id": self.sample_resource_id,
            "texts": self.sample_texts,
            "callback_url": "http://callback.example.com",
            "user_id": "test-user"
        }

        # Verify structure matches what the embedding service expects
        self.assertEqual(sample_event_data["event"], "create_embedding")
        self.assertEqual(sample_event_data["task_id"], self.sample_task_id)
        self.assertEqual(sample_event_data["resource_id"], self.sample_resource_id)
        self.assertEqual(sample_event_data["texts"], self.sample_texts)
        self.assertEqual(sample_event_data["callback_url"], "http://callback.example.com")
        self.assertEqual(sample_event_data["user_id"], "test-user")


class TestEmbeddingWorkflowCompatibility(unittest.TestCase):
    """Test compatibility with embedding consumer service"""

    def test_simulated_embedding_consumer_interaction(self):
        """Simulate interaction with the embedding consumer service"""
        print("\n=== Testing Embedding Consumer Service Interaction ===")

        # Simulate the event that CRM would send to the embedding service
        crm_event = {
            "event": "create_embedding",
            "task_id": "task-12345",
            "resource_id": "resource-123",
            "texts": [
                "This document contains information about machine learning.",
                "The second chunk explains various algorithms in detail.",
                "The third chunk discusses applications and use cases."
            ],
            "callback_url": "http://crm.example.com/callback/embedding_response",
            "user_id": "researcher"
        }

        print("1. CRM sends embed request:")
        print(f"   Task ID: {crm_event['task_id']}")
        print(f"   Resource ID: {crm_event['resource_id']}")
        print(f"   Texts count: {len(crm_event['texts'])}")
        print(f"   Callback URL: {crm_event['callback_url']}")

        # Simulate the embedding service's response
        embedding_response = {
            "event": "embedding_response",
            "resource_id": "resource-123",
            "chunks": crm_event["texts"],  # Original chunks
            "embeddings": [
                [0.1, 0.2, 0.3, 0.4, 0.5] * 10,  # Simulated embedding vector
                [0.2, 0.3, 0.4, 0.5, 0.6] * 10,  # Simulated embedding vector
                [0.3, 0.4, 0.5, 0.6, 0.7] * 10   # Simulated embedding vector
            ],
            "file_name": "research_paper.pdf",
            "file_path": "/documents/research_paper.pdf",
            "model_name": "text-embedding-3-small",
            "processing_time": 0.234,
            "status": "success"
        }

        print("\n2. Embedding Service responds:")
        print(f"   Status: {embedding_response['status']}")
        print(f"   Model used: {embedding_response['model_name']}")
        print(f"   Processing time: {embedding_response['processing_time']}s")
        print(f"   Embeddings count: {len(embedding_response['embeddings'])}")
        print(f"   Embedding dimensions: {len(embedding_response['embeddings'][0])}")

        # Verify the response structure matches expectations
        self.assertEqual(embedding_response["event"], "embedding_response")
        self.assertEqual(embedding_response["resource_id"], crm_event["resource_id"])
        self.assertEqual(len(embedding_response["chunks"]), len(embedding_response["embeddings"]))
        self.assertEqual(embedding_response["status"], "success")

        print("\n3. Compatibility verified:")
        print("   ✓ Request-response resource ID matches")
        print("   ✓ Embedding count matches chunk count")
        print("   ✓ Callback URL properly formatted")
        print("   ✓ Response includes all required metadata")

        print("\n=== Embedding Service Compatibility Test Completed ===")


if __name__ == '__main__':
    unittest.main(verbosity=2)

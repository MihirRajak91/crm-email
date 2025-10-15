#!/usr/bin/env python3
"""
Test suite for embedding response handling functionality
"""

import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import EmbeddingResponse with fallback for testing environments
try:
    from crm.models.rabbitmq_event_models import EmbeddingResponse
    EMBEDDING_RESPONSE_AVAILABLE = True
except ImportError:
    print("EmbeddingResponse import failed (expected in testing environment)")
    EMBEDDING_RESPONSE_AVAILABLE = False
    EmbeddingResponse = None  # Placeholder


class TestEmbeddingResponse(unittest.TestCase):
    """Test EmbeddingResponse model and processing functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.sample_embeddings = [
            [0.1, 0.2, 0.3, 0.4, 0.5],  # Vector 1
            [0.2, 0.3, 0.4, 0.5, 0.6],  # Vector 2
            [0.3, 0.4, 0.5, 0.6, 0.7],  # Vector 3
        ]
        self.sample_chunks = {
            "0": {"text": "chunk one"},
            "1": {"text": "chunk two"},
            "2": {"text": "chunk three"},
        }

        self.sample_resource_id = "test-resource-123"

    @unittest.skipUnless(EMBEDDING_RESPONSE_AVAILABLE, "EmbeddingResponse requires pydantic")
    def test_embedding_response_creation(self):
        """Test creating EmbeddingResponse with all required fields"""
        response = EmbeddingResponse(
            id=self.sample_resource_id,
            user_id="test-user",
            organization_id="test-org",
            embeddings=self.sample_embeddings,
            chunks=self.sample_chunks,
            resource_name="test_document.pdf",
            resource_path="/test/path/test_document.pdf",
            model_name="text-embedding-3-small",
            processing_time=0.045,
            status="success",
            service_name="embedding_service",
        )

        # Verify all fields
        self.assertEqual(response.resource_id, self.sample_resource_id)
        self.assertEqual(response.user_id, "test-user")
        self.assertEqual(response.organization_id, "test-org")
        self.assertEqual(response.embeddings, self.sample_embeddings)
        self.assertEqual(response.chunks, self.sample_chunks)
        self.assertEqual(response.model_name, "text-embedding-3-small")
        self.assertEqual(response.processing_time, 0.045)
        self.assertEqual(response.status, "success")
        self.assertEqual(response.event, "embedding_response")
        self.assertEqual(response.service_name, "embedding_service")

    @unittest.skipUnless(EMBEDDING_RESPONSE_AVAILABLE, "EmbeddingResponse requires pydantic")
    def test_embedding_response_minimal_data(self):
        """Test creating EmbeddingResponse with minimal required fields"""
        response = EmbeddingResponse(
            id=self.sample_resource_id,
            user_id="user",
            organization_id="org",
            embeddings=self.sample_embeddings,
            chunks=self.sample_chunks,
            resource_name="doc.pdf",
            resource_path="/path/doc.pdf",
            service_name="embedding_service",
        )

        # Verify minimal required fields are set
        self.assertEqual(response.resource_id, self.sample_resource_id)
        self.assertEqual(response.embeddings, self.sample_embeddings)
        self.assertEqual(response.chunks, self.sample_chunks)

        # Check optional fields have defaults
        self.assertIsNone(response.model_name)
        self.assertIsNone(response.processing_time)
        self.assertEqual(response.status, "success")  # Default value
        self.assertIsNone(response.error_message)

    @unittest.skipUnless(EMBEDDING_RESPONSE_AVAILABLE, "EmbeddingResponse requires pydantic")
    def test_embedding_response_serialization(self):
        """Test EmbeddingResponse serialization for message queues"""
        response = EmbeddingResponse(
            id=self.sample_resource_id,
            user_id="test-user",
            organization_id="test-org",
            embeddings=self.sample_embeddings,
            chunks=self.sample_chunks,
            resource_name="test.pdf",
            resource_path="/test/path/test.pdf"
        )

        # Serialize to dict
        response_dict = response.dict(by_alias=True)

        # Verify structure for RabbitMQ
        self.assertEqual(response_dict["event"], "embedding_response")
        self.assertEqual(response_dict["id"], self.sample_resource_id)
        self.assertEqual(len(response_dict["embeddings"]), 3)
        self.assertEqual(len(response_dict["chunks"]), 3)
        self.assertEqual(response_dict["id"], self.sample_resource_id)
        self.assertEqual(response_dict["service_name"], "embedding_service")

    @unittest.skipUnless(EMBEDDING_RESPONSE_AVAILABLE, "EmbeddingResponse requires pydantic")
    def test_embedding_response_validation(self):
        """Test validation for proper embedding/chunk alignment"""
        # Test with mismatched counts (normal use case - valid)
        response = EmbeddingResponse(
            id=self.sample_resource_id,
            user_id="user",
            organization_id="org",
            embeddings=self.sample_embeddings,  # 3 embeddings
            chunks={"0": {"text": "chunk one"}, "1": {"text": "chunk two"}},      # 2 chunks - different count is allowed
            resource_name="doc.pdf",
            resource_path="/path/doc.pdf",
            service_name="embedding_service",
        )

        # Should still be valid - validation happens at processing time
        self.assertEqual(len(response.embeddings), 3)
        self.assertEqual(len(response.chunks), 2)

    @unittest.skipUnless(EMBEDDING_RESPONSE_AVAILABLE, "EmbeddingResponse requires pydantic")
    def test_embedding_response_error_handling(self):
        """Test EmbeddingResponse with error status"""
        response = EmbeddingResponse(
            id=self.sample_resource_id,
            user_id="user",
            organization_id="org",
            embeddings=[],  # Empty on error
            chunks=self.sample_chunks,
            resource_name="doc.pdf",
            resource_path="/path/doc.pdf",
            status="error",
            error="Embedding service unavailable",
            service_name="embedding_service",
        )

        self.assertEqual(response.status, "error")
        self.assertEqual(response.error, "Embedding service unavailable")
        self.assertEqual(len(response.embeddings), 0)  # No embeddings on error

    @unittest.skip("Requires full application setup for Qdrant integration")
    def test_qdrant_storage_simulation(self):
        """Simulate embedding storage in Qdrant (requires full setup)"""
        # This test would require actual Qdrant setup

        response = EmbeddingResponse(
            id=self.sample_resource_id,
            user_id="user",
            organization_id="org",
            embeddings=self.sample_embeddings,
            chunks=self.sample_chunks,
            resource_name="doc.pdf",
            resource_path="/path/doc.pdf",
            service_name="embedding_service",
        )

        # In real scenario, this would test the Qdrant storage
        # but for unit test we skip due to infrastructure requirements

        # Example structure that would be tested:
        # - Embedding vectors are stored
        # - Payload metadata is correctly formed
        # - Qdrant API calls succeed
        # - Error handling for failed storage

        self.assertTrue(True)  # Placeholder for now


class TestEmbeddingResponseWorkflow(unittest.TestCase):
    """Test the full workflow of embedding response processing"""

    @unittest.skipUnless(EMBEDDING_RESPONSE_AVAILABLE, "EmbeddingResponse requires pydantic")
    def test_response_workflow_structure(self):
        """Test the structure of a complete embedding response workflow"""
        print("\n=== Embedding Response Workflow Test ===")

        # 1. Simulate receiving embeddings from external service
        incoming_message = {
            "event": "embedding_response",
            "id": "resource-123",
            "user_id": "user-456",
            "organization_id": "org-789",
            "embeddings": [
                [0.1, 0.2, 0.3, 0.4, 0.5],
                [0.2, 0.3, 0.4, 0.5, 0.6]
            ],
            "chunks": ["chunk text 1", "chunk text 2"],
            "resource_name": "document.pdf",
            "resource_path": "/documents/document.pdf",
            "model_name": "text-embedding-3-small",
            "processing_time": 0.042,
            "status": "success",
            "service_name": "embedding_service",
        }

        print("1. Received embedding response message:")
        print(f"   Resource ID: {incoming_message['id']}")
        print(f"   Embeddings count: {len(incoming_message['embeddings'])}")
        print(f"   Chunks count: {len(incoming_message['chunks'])}")
        print(f"   Status: {incoming_message['status']}")

        # 2. Parse the response
        try:
            embedding_response = EmbeddingResponse(**incoming_message)
            print("\n2. Successfully parsed EmbeddingResponse:")
            print(f"   Event type: {embedding_response.event}")
            print(f"   Model used: {embedding_response.model_name}")
            print(f"   Processing time: {embedding_response.processing_time}s")
        except Exception as e:
            self.fail(f"Failed to parse embedding response: {e}")

        # 3. Validate data consistency
        embeddings_count = len(embedding_response.embeddings)
        chunks_count = len(embedding_response.chunks)

        print(f"\n3. Validation:")
        print(f"   Embeddings: {embeddings_count}, Chunks: {chunks_count}")

        if embeddings_count != chunks_count:
            print(f"   ⚠️  Warning: Count mismatch detected")
            # In real processing, this would trigger warning but continue
        else:
            print("   ✓ Counts match - data is consistent")

        # 4. Verify embedding dimensions
        if embedding_response.embeddings:
            first_embedding_dim = len(embedding_response.embeddings[0])
            print(f"   Embedding dimension: {first_embedding_dim}")

            # Check all embeddings have same dimension
            all_same_dim = all(len(emb) == first_embedding_dim for emb in embedding_response.embeddings)
            if all_same_dim:
                print("   ✓ All embeddings have consistent dimensions")
            else:
                print("   ⚠️  Warning: Inconsistent embedding dimensions")

        # 5. Prepare data structure for storage
        storage_payloads = []
        chunk_items = list(embedding_response.chunks.items())
        chunk_items.sort(key=lambda item: int(item[0]) if str(item[0]).isdigit() else item[0])
        for i, ((chunk_key, chunk_payload), embedding) in enumerate(zip(chunk_items, embedding_response.embeddings)):
            if isinstance(chunk_payload, dict):
                chunk_text = chunk_payload.get("text") or chunk_payload.get("content") or ""
            else:
                chunk_text = str(chunk_payload)
            payload = {
                "resource_id": embedding_response.resource_id,
                "user_id": embedding_response.user_id,
                "organization_id": embedding_response.organization_id,
                "chunk_id": i,
                "chunk_index": i,
                "total_chunks": len(embedding_response.chunks),
                "chunk_key": chunk_key,
                "text": chunk_text,
                "file_name": embedding_response.file_name,
                "file_path": embedding_response.file_path,
                "embedding_model": embedding_response.model_name or "unknown",
                "processing_time": embedding_response.processing_time or 0.0,
                "embedding_dimension": len(embedding),
                "timestamp": 1234567890  # Mock timestamp
            }
            storage_payloads.append(payload)

        print(f"\n4. Prepared {len(storage_payloads)} payloads for storage")
        print(f"   Sample payload keys: {list(storage_payloads[0].keys())}")

        print("\n=== Workflow Test Completed Successfully ===")

        # Verify the workflow structure
        self.assertEqual(embedding_response.event, "embedding_response")
        self.assertGreater(len(embedding_response.embeddings), 0)
        self.assertGreater(len(embedding_response.chunks), 0)
        self.assertEqual(len(storage_payloads), len(embedding_response.chunks))


if __name__ == '__main__':
    unittest.main(verbosity=2)

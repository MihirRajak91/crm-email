#!/usr/bin/env python3
"""
Test script for the new tiktoken-based chunking implementation.
"""

import sys
from pathlib import Path

# Ensure repository root is discoverable when executing directly
sys.path.append(str(Path(__file__).resolve().parents[1]))

from crm.utils.token_text_splitter import TikTokenTextSplitter
from crm.configs.performance_config import perf_config

def test_basic_token_splitting():
    """Test basic token-based text splitting."""
    print("=== Basic Token Splitting Test ===")
    
    splitter = TikTokenTextSplitter(max_tokens=50, overlap_tokens=10)
    
    # Test text
    test_text = """
    This is a longer piece of text that should be split into multiple chunks based on token count rather than character count. 
    Token-based splitting is more accurate for embedding models and API cost estimation. 
    It ensures that chunks align with how the model actually processes text, leading to better performance and more predictable costs.
    """
    
    chunks = splitter.split_text(test_text)
    
    print(f"Original text tokens: {splitter.count_tokens(test_text)}")
    print(f"Number of chunks: {len(chunks)}")
    
    for i, chunk in enumerate(chunks):
        token_count = splitter.count_tokens(chunk)
        print(f"\nChunk {i+1} ({token_count} tokens):")
        print(f"  '{chunk[:100]}...'")
    
    return len(chunks) > 1

def test_timestamp_aware_splitting():
    """Test timestamp-aware splitting for video transcripts."""
    print("\n=== Timestamp-Aware Splitting Test ===")
    
    splitter = TikTokenTextSplitter(max_tokens=100, overlap_tokens=20)
    
    # Mock video transcript with embedded timestamps
    transcript = """[0.0s-5.2s] Welcome to our sales training program. [5.2s-12.1s] Today we'll cover three key strategies for building customer relationships. [12.1s-18.9s] First is active listening and showing genuine empathy for customer concerns. [18.9s-25.4s] This involves mirroring their communication style and asking thoughtful follow-up questions. [25.4s-32.1s] Second strategy is understanding customer needs through effective questioning techniques. [32.1s-38.7s] Ask open-ended questions that encourage customers to share their challenges and goals."""
    
    chunks = splitter.split_text_with_timestamps(transcript)
    
    print(f"Original transcript tokens: {splitter.count_tokens(transcript)}")
    print(f"Number of timestamp-aware chunks: {len(chunks)}")
    
    for i, chunk in enumerate(chunks):
        token_count = splitter.count_tokens(chunk)
        print(f"\nChunk {i+1} ({token_count} tokens):")
        print(f"  '{chunk}'")
    
    return len(chunks) > 0

def test_cost_estimation():
    """Test cost estimation functionality."""
    print("\n=== Cost Estimation Test ===")
    
    splitter = TikTokenTextSplitter()
    
    test_text = "This is a test text for cost estimation using tiktoken with OpenAI embedding models."
    
    token_count = splitter.count_tokens(test_text)
    estimated_cost = splitter.estimate_cost(test_text)
    
    print(f"Text: '{test_text}'")
    print(f"Token count: {token_count}")
    print(f"Estimated embedding cost: ${estimated_cost:.6f}")
    
    return token_count > 0

def test_performance_config():
    """Test integration with performance config."""
    print("\n=== Performance Config Integration Test ===")
    
    print(f"Max tokens per chunk: {perf_config.max_tokens_per_chunk}")
    print(f"Token overlap: {perf_config.token_overlap}")
    
    # Create splitter with config values
    splitter = TikTokenTextSplitter(
        max_tokens=perf_config.max_tokens_per_chunk,
        overlap_tokens=perf_config.token_overlap
    )
    
    test_text = "Integration test with performance configuration values. " * 50
    chunks = splitter.split_text(test_text)
    
    print(f"Created {len(chunks)} chunks using config values")
    
    return len(chunks) > 0

def main():
    """Run all tests."""
    print("Testing TikToken-based Chunking Implementation")
    print("=" * 50)
    
    tests = [
        test_basic_token_splitting,
        test_timestamp_aware_splitting,
        test_cost_estimation,
        test_performance_config
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print(f"✓ {test.__name__}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            results.append(False)
            print(f"✗ {test.__name__}: ERROR - {e}")
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Token-based chunking is ready to use.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

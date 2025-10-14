#!/usr/bin/env python3
"""
Compare character-based vs token-based chunking methods.
"""

import sys
from pathlib import Path

# Ensure repository root is on the path for local execution
sys.path.append(str(Path(__file__).resolve().parents[1]))

from langchain.text_splitter import RecursiveCharacterTextSplitter
from crm.utils.token_text_splitter import TikTokenTextSplitter

def compare_chunking_methods():
    """Compare character-based vs token-based chunking."""
    
    # Sample text (video transcript style)
    sample_text = """[0.0s-5.2s] Welcome to our comprehensive sales training program. [5.2s-12.1s] Today we'll be covering three essential strategies for building lasting customer relationships. [12.1s-18.9s] The first strategy is active listening and showing genuine empathy for customer concerns and pain points. [18.9s-25.4s] This involves carefully mirroring their communication style and asking thoughtful, open-ended follow-up questions. [25.4s-32.1s] The second strategy focuses on understanding customer needs through effective questioning techniques and careful observation. [32.1s-38.7s] Ask open-ended questions that encourage customers to share their specific challenges and long-term business goals."""
    
    print("=== CHUNKING METHOD COMPARISON ===")
    print(f"Original text length: {len(sample_text)} characters")
    print(f"Sample: {sample_text[:100]}...\n")
    
    # Character-based chunking (old method)
    print("--- CHARACTER-BASED CHUNKING (Old Method) ---")
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )
    char_chunks = char_splitter.split_text(sample_text)
    
    print(f"Number of chunks: {len(char_chunks)}")
    for i, chunk in enumerate(char_chunks):
        print(f"Chunk {i+1} ({len(chunk)} chars): {chunk}")
        print()
    
    # Token-based chunking (new method)
    print("--- TOKEN-BASED CHUNKING (New Method) ---")
    token_splitter = TikTokenTextSplitter(max_tokens=200, overlap_tokens=50)
    token_chunks = token_splitter.split_text(sample_text)
    
    total_tokens = token_splitter.count_tokens(sample_text)
    estimated_cost = token_splitter.estimate_cost(sample_text)
    
    print(f"Total tokens in original: {total_tokens}")
    print(f"Estimated embedding cost: ${estimated_cost:.6f}")
    print(f"Number of chunks: {len(token_chunks)}")
    
    for i, chunk in enumerate(token_chunks):
        token_count = token_splitter.count_tokens(chunk)
        print(f"Chunk {i+1} ({token_count} tokens): {chunk}")
        print()
    
    # Timestamp-aware chunking (enhanced method)
    print("--- TIMESTAMP-AWARE TOKEN CHUNKING (Enhanced Method) ---")
    timestamp_chunks = token_splitter.split_text_with_timestamps(sample_text)
    
    print(f"Number of timestamp-aware chunks: {len(timestamp_chunks)}")
    for i, chunk in enumerate(timestamp_chunks):
        token_count = token_splitter.count_tokens(chunk)
        print(f"Chunk {i+1} ({token_count} tokens): {chunk}")
        print()
    
    # Summary comparison
    print("=== SUMMARY COMPARISON ===")
    print(f"Character-based chunks: {len(char_chunks)}")
    print(f"Token-based chunks: {len(token_chunks)}")
    print(f"Timestamp-aware chunks: {len(timestamp_chunks)}")
    print(f"Total tokens: {total_tokens}")
    print(f"Estimated cost: ${estimated_cost:.6f}")
    
    print("\n=== ADVANTAGES OF TOKEN-BASED CHUNKING ===")
    print("✓ More accurate for embedding models (token-aligned)")
    print("✓ Better cost estimation and control")
    print("✓ 3-6x faster tokenization than alternatives")
    print("✓ Consistent chunk sizes in token space")
    print("✓ Preserves timestamp boundaries")
    print("✓ Better semantic coherence")

if __name__ == "__main__":
    compare_chunking_methods()

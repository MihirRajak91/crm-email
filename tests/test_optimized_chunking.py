#!/usr/bin/env python3
"""
Test the optimized chunking configuration.
"""

import sys
from pathlib import Path

# Ensure repository root is on the path when running the script directly
sys.path.append(str(Path(__file__).resolve().parents[1]))

from crm.configs.performance_config import perf_config
from crm.utils.token_text_splitter import TikTokenTextSplitter

def test_optimized_settings():
    """Test the new optimized chunking settings."""
    
    print("=== OPTIMIZED CHUNKING CONFIGURATION TEST ===")
    print()
    
    # Show new configuration
    print("🎯 NEW OPTIMIZED SETTINGS:")
    print(f"  General documents: {perf_config.max_tokens_per_chunk} tokens, {perf_config.token_overlap} overlap")
    print(f"  Video transcripts: {perf_config.video_max_tokens} tokens, {perf_config.video_token_overlap} overlap") 
    print(f"  Local embeddings: {perf_config.local_max_tokens} tokens, {perf_config.local_token_overlap} overlap")
    print()
    
    # Create optimized splitters
    general_splitter = TikTokenTextSplitter(
        max_tokens=perf_config.max_tokens_per_chunk,
        overlap_tokens=perf_config.token_overlap
    )
    
    video_splitter = TikTokenTextSplitter(
        max_tokens=perf_config.video_max_tokens, 
        overlap_tokens=perf_config.video_token_overlap
    )
    
    # Test with sample video transcript
    video_transcript = """[0.0s-5.2s] Welcome to our comprehensive sales training program designed to enhance your customer relationship building skills. [5.2s-12.1s] Today we'll be covering three essential strategies that have been proven effective in building lasting customer relationships and driving sales success. [12.1s-18.9s] The first strategy is active listening and showing genuine empathy for customer concerns and pain points. [18.9s-25.4s] This involves carefully mirroring their communication style and asking thoughtful, open-ended follow-up questions that demonstrate your understanding. [25.4s-32.1s] The second strategy focuses on understanding customer needs through effective questioning techniques and careful observation of their responses. [32.1s-38.7s] Ask open-ended questions that encourage customers to share their specific challenges and long-term business goals. [38.7s-45.3s] The third strategy involves building trust through consistent follow-through on promises and maintaining regular communication. [45.3s-52.0s] Always deliver on your commitments and keep customers informed about progress and potential issues. [52.0s-58.5s] Remember that trust is built over time through small actions and consistent behavior patterns."""
    
    print("📹 VIDEO TRANSCRIPT CHUNKING TEST:")
    print(f"Original transcript: {video_splitter.count_tokens(video_transcript)} tokens")
    
    video_chunks = video_splitter.split_text_with_timestamps(video_transcript)
    video_cost = video_splitter.estimate_cost(video_transcript)
    
    print(f"Chunks created: {len(video_chunks)}")
    print(f"Estimated cost: ${video_cost:.6f}")
    
    for i, chunk in enumerate(video_chunks):
        token_count = video_splitter.count_tokens(chunk)
        print(f"  Chunk {i+1}: {token_count} tokens")
        print(f"    Preview: {chunk[:100]}...")
        print()
    
    # Test with document content
    document_text = """
    Customer relationship management (CRM) is a technology for managing all your company's relationships and interactions with customers and potential customers. The goal is simple: Improve business relationships to grow your business. A CRM system helps companies stay connected to customers, streamline processes, and improve profitability.
    
    When people talk about CRM, they are usually referring to a CRM system, a tool that helps with contact management, sales management, agent productivity, and more. CRM tools can now be used to manage customer relationships across the entire customer lifecycle, spanning marketing, sales, digital commerce, and customer service interactions.
    
    A CRM solution helps you focus on your organization's relationships with individual people — including customers, service users, colleagues, or suppliers — throughout your lifecycle with them, including finding new customers, winning their business, and providing support and additional services throughout the relationship.
    """ * 3  # Make it longer to test chunking
    
    print("📄 DOCUMENT CHUNKING TEST:")
    print(f"Original document: {general_splitter.count_tokens(document_text)} tokens")
    
    doc_chunks = general_splitter.split_text(document_text)
    doc_cost = general_splitter.estimate_cost(document_text)
    
    print(f"Chunks created: {len(doc_chunks)}")
    print(f"Estimated cost: ${doc_cost:.6f}")
    
    for i, chunk in enumerate(doc_chunks):
        token_count = general_splitter.count_tokens(chunk)
        print(f"  Chunk {i+1}: {token_count} tokens")
        print(f"    Preview: {chunk[:100].strip()}...")
        print()
    
    # Comparison with old settings
    print("⚖️ OLD vs NEW COMPARISON:")
    old_splitter = TikTokenTextSplitter(max_tokens=200, overlap_tokens=50)
    old_chunks = old_splitter.split_text_with_timestamps(video_transcript)
    
    print(f"Old config (200 tokens): {len(old_chunks)} chunks")
    print(f"New config (800 tokens): {len(video_chunks)} chunks") 
    print(f"Chunk reduction: {len(old_chunks) - len(video_chunks)} fewer chunks ({((len(old_chunks) - len(video_chunks)) / len(old_chunks) * 100):.0f}% reduction)")
    print(f"API call reduction: {len(old_chunks) - len(video_chunks)} fewer calls")
    print()
    
    print("✅ OPTIMIZATION BENEFITS:")
    print("  🎯 Better context preservation (larger meaningful chunks)")
    print("  💰 Lower API costs (fewer embedding calls)")
    print("  ⚡ Better retrieval quality (optimal chunk sizes)")
    print("  🧠 Improved semantic coherence")
    print("  📊 Industry best practices (20% overlap)")

if __name__ == "__main__":
    test_optimized_settings()

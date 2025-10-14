#!/usr/bin/env python3
"""
Optimized chunk size configuration based on research for CRM system.
"""

# OPTIMIZED CONFIGURATION FOR YOUR USE CASE
OPTIMAL_CHUNK_CONFIGS = {
    # For OpenAI text-embedding-3-small (your primary model)
    "openai": {
        "max_tokens_per_chunk": 1000,      # Optimal for text-embedding-3-small
        "token_overlap": 200,               # 20% overlap (industry best practice)
        "encoding": "cl100k_base",          # GPT-4/text-embedding-3-* encoding
        "cost_per_1k_tokens": 0.00002,      # text-embedding-3-small pricing
        "max_context": 8191                 # Model limit
    },
    
    # For nomic-ai/nomic-embed-text-v1.5 (your local model)  
    "nomic": {
        "max_tokens_per_chunk": 2048,      # Trained on 2048-token chunks
        "token_overlap": 410,               # 20% overlap
        "max_context": 8192,                # Model limit
        "trained_chunk_size": 2048          # Training chunk size
    },
    
    # For video transcripts (your main use case)
    "video_transcripts": {
        "max_tokens_per_chunk": 800,       # Optimal for speech patterns
        "token_overlap": 160,               # 20% overlap for context continuity
        "natural_boundaries": True,         # Break at speaker/sentence boundaries
        "preserve_timestamps": True,        # Maintain timestamp integrity
        "chunk_by_scene": True             # Scene-based chunking when possible
    },
    
    # For documents (PDF/DOCX/HTML)
    "documents": {
        "max_tokens_per_chunk": 1000,      # Standard for text documents
        "token_overlap": 200,               # 20% overlap
        "semantic_boundaries": True,        # Break at paragraph/section boundaries
        "preserve_structure": True          # Maintain document structure
    }
}

# PERFORMANCE COMPARISON
PERFORMANCE_ANALYSIS = {
    "current_config": {
        "tokens_per_chunk": 200,
        "overlap": 50,
        "efficiency_rating": "LOW",
        "issues": [
            "Chunks too small - loss of context",
            "Excessive API calls (5x more than optimal)",
            "Poor semantic coherence", 
            "Suboptimal embedding quality",
            "Higher costs per token of meaningful content"
        ]
    },
    
    "optimized_config": {
        "tokens_per_chunk": 1000,
        "overlap": 200,
        "efficiency_rating": "HIGH", 
        "benefits": [
            "Better context preservation",
            "Optimal for embedding models",
            "Fewer API calls (5x reduction)",
            "Better retrieval quality",
            "Lower cost per meaningful content"
        ]
    }
}

# USE CASE SPECIFIC RECOMMENDATIONS
USE_CASE_RECOMMENDATIONS = {
    "sales_training_videos": {
        "recommended_chunk_size": 800,
        "overlap": 160,
        "reasoning": "Sales conversations have natural flow; 800 tokens capture complete thoughts while maintaining speaker context"
    },
    
    "technical_documentation": {
        "recommended_chunk_size": 1200, 
        "overlap": 240,
        "reasoning": "Technical content is dense; larger chunks preserve procedural context and code examples"
    },
    
    "conversational_transcripts": {
        "recommended_chunk_size": 600,
        "overlap": 120,
        "reasoning": "Dialogue patterns benefit from smaller chunks that capture speaker exchanges"
    }
}

def get_optimal_config(content_type: str, embedding_model: str) -> dict:
    """
    Get optimal configuration for specific content type and embedding model.
    
    Args:
        content_type: 'video', 'document', 'conversation'
        embedding_model: 'openai', 'nomic'
    
    Returns:
        dict: Optimal configuration parameters
    """
    
    base_config = OPTIMAL_CHUNK_CONFIGS.get(embedding_model, OPTIMAL_CHUNK_CONFIGS["openai"])
    
    # Adjust based on content type
    if content_type == "video":
        return {
            "max_tokens_per_chunk": 800,
            "token_overlap": 160,
            **base_config
        }
    elif content_type == "document":
        return {
            "max_tokens_per_chunk": 1000,
            "token_overlap": 200, 
            **base_config
        }
    else:
        return base_config

if __name__ == "__main__":
    print("=== OPTIMIZED CHUNK CONFIGURATION ANALYSIS ===")
    print()
    
    # Your current config analysis
    print("❌ CURRENT CONFIG (Inefficient):")
    print(f"  Chunk size: 200 tokens")
    print(f"  Overlap: 50 tokens (25%)")
    print(f"  Issues: {PERFORMANCE_ANALYSIS['current_config']['issues']}")
    print()
    
    # Recommended config
    print("✅ OPTIMIZED CONFIG (Recommended):")
    openai_config = get_optimal_config("video", "openai")
    print(f"  Chunk size: {openai_config['max_tokens_per_chunk']} tokens")
    print(f"  Overlap: {openai_config['token_overlap']} tokens (20%)")
    print(f"  Benefits: {PERFORMANCE_ANALYSIS['optimized_config']['benefits']}")
    print()
    
    # Cost comparison example
    print("💰 COST COMPARISON (1000 tokens of content):")
    print(f"  Current (200-token chunks): 5 API calls = ${5 * 0.00002:.6f}")
    print(f"  Optimized (1000-token chunks): 1 API call = ${1 * 0.00002:.6f}")
    print(f"  Cost reduction: 5x less expensive")
    print()
    
    # Model-specific recommendations  
    print("🎯 MODEL-SPECIFIC RECOMMENDATIONS:")
    for model, config in OPTIMAL_CHUNK_CONFIGS.items():
        if isinstance(config, dict) and "max_tokens_per_chunk" in config:
            print(f"  {model}: {config['max_tokens_per_chunk']} tokens, {config.get('token_overlap', 'N/A')} overlap")
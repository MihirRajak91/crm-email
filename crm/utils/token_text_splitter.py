import tiktoken
from typing import List, Optional
from crm.utils.logger import logger

class TikTokenTextSplitter:
    """
    Token-based text splitter using tiktoken for more accurate chunking.
    Optimized for OpenAI embedding models and better cost estimation.
    """
    
    def __init__(
        self, 
        encoding_name: str = "cl100k_base",  # GPT-4/GPT-3.5/text-embedding-3-*
        max_tokens: int = 200,
        overlap_tokens: int = 50
    ):
        """
        Initialize the token-based text splitter.
        
        Args:
            encoding_name: tiktoken encoding name (cl100k_base for latest models)
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of overlapping tokens between chunks
        """
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        logger.info(f"[TokenSplitter] Using {encoding_name} encoding, max_tokens={max_tokens}, overlap={overlap_tokens}")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))
    
    def split_text(self, text: str) -> List[str]:
        """
        Split text into token-based chunks with overlap.
        
        Args:
            text: Input text to split
            
        Returns:
            List of text chunks
        """
        if not text.strip():
            return []
        
        # Encode the entire text
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)
        
        if total_tokens <= self.max_tokens:
            return [text]
        
        chunks = []
        start_idx = 0
        
        while start_idx < total_tokens:
            # Calculate end index for this chunk
            end_idx = min(start_idx + self.max_tokens, total_tokens)
            
            # Extract chunk tokens
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Clean up and add to chunks
            if chunk_text.strip():
                chunks.append(chunk_text.strip())
            
            # Move start position with overlap
            if end_idx >= total_tokens:
                break
            start_idx = end_idx - self.overlap_tokens
            
            # Prevent infinite loops
            if start_idx <= 0:
                start_idx = 1
        
        logger.debug(f"[TokenSplitter] Split {total_tokens} tokens into {len(chunks)} chunks")
        return chunks
    
    def split_text_with_timestamps(self, text: str) -> List[str]:
        """
        Enhanced splitting that preserves timestamp boundaries.
        Designed for video transcripts with embedded timestamps.
        
        Args:
            text: Text with embedded timestamps like "[1.2s-5.4s] content"
            
        Returns:
            List of text chunks preserving timestamp integrity
        """
        import re
        
        if not text.strip():
            return []
        
        # Find all timestamp segments
        timestamp_pattern = r'(\[\d+\.?\d*s?-\d+\.?\d*s?\][^[]*)'
        segments = re.findall(timestamp_pattern, text)
        
        if not segments:
            # No timestamps found, use regular splitting
            return self.split_text(text)
        
        # Process segments with token-aware chunking
        chunks = []
        current_chunk_tokens = []
        current_chunk_text = ""
        
        for segment in segments:
            segment_tokens = self.encoding.encode(segment)
            segment_token_count = len(segment_tokens)
            
            # Check if adding this segment would exceed max tokens
            if len(current_chunk_tokens) + segment_token_count > self.max_tokens and current_chunk_tokens:
                # Finalize current chunk
                if current_chunk_text.strip():
                    chunks.append(current_chunk_text.strip())
                
                # Start new chunk with overlap
                if len(chunks) > 0 and self.overlap_tokens > 0:
                    # Get last N tokens from previous chunk for overlap
                    overlap_tokens = current_chunk_tokens[-self.overlap_tokens:]
                    overlap_text = self.encoding.decode(overlap_tokens)
                    current_chunk_text = overlap_text + " " + segment
                    current_chunk_tokens = overlap_tokens + segment_tokens
                else:
                    current_chunk_text = segment
                    current_chunk_tokens = segment_tokens
            else:
                # Add to current chunk
                if current_chunk_text:
                    current_chunk_text += " " + segment
                    current_chunk_tokens.extend(segment_tokens)
                else:
                    current_chunk_text = segment
                    current_chunk_tokens = segment_tokens
        
        # Add final chunk
        if current_chunk_text.strip():
            chunks.append(current_chunk_text.strip())
        
        logger.debug(f"[TokenSplitter] Created {len(chunks)} timestamp-aware chunks")
        return chunks

    def estimate_cost(self, text: str, cost_per_1k_tokens: float = 0.00010) -> float:
        """
        Estimate OpenAI API cost for embedding this text.
        
        Args:
            text: Input text
            cost_per_1k_tokens: Cost per 1000 tokens (text-embedding-3-small default)
            
        Returns:
            Estimated cost in USD
        """
        token_count = self.count_tokens(text)
        return (token_count / 1000) * cost_per_1k_tokens
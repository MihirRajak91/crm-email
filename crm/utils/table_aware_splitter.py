"""
Table-aware text splitter that preserves table integrity during chunking.
Uses tiktoken for precise token counting and cost estimation.
"""

import re
import tiktoken
from typing import List, Tuple, Dict, Any, Optional
from crm.utils.logger import logger


class TableAwareTextSplitter:
    """
    Text splitter that detects and preserves Markdown tables during chunking.
    """

    def __init__(self, max_tokens: int = 1000, overlap_tokens: int = 200,
                 encoding_name: str = "cl100k_base", context_window_tokens: int = 200):
        """
        Initialize the table-aware splitter with tiktoken support and semantic context preservation.

        Args:
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of overlapping tokens between chunks
            encoding_name: tiktoken encoding name for the model
            context_window_tokens: Tokens to preserve around tables for semantic context (default 200)
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding_name = encoding_name
        self.context_window_tokens = context_window_tokens  # New: tokens to keep around tables

        # Initialize tiktoken encoding directly
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
            logger.info(f"[TableSplitter] Using {encoding_name} encoding, max_tokens={max_tokens}, overlap={overlap_tokens}, context={context_window_tokens}")
        except Exception as e:
            logger.error(f"[TableSplitter] Failed to initialize tiktoken: {e}")
            # Fallback to simple character approximation
            self.encoding = None

        # Regex patterns for detecting Markdown tables
        self.table_patterns = [
            # Standard Markdown table with headers and separator row
            r'\|[^\n]*\|[\s]*\n\|[\s\-\|:]+\|[\s]*\n(?:\|[^\n]*\|[\s]*\n)+',
            # Simple table without headers (just rows with pipes)
            r'\|[^\n]*\|[\s]*\n(?:\|[^\n]*\|[\s]*\n){2,}',
            # HTML table tags (fallback for converted content)
            r'<table[^>]*>.*?</table>',
            # Alternative pattern for tables with consistent pipe separators
            r'^\|.*\|\s*$[\r\n]+\|[\s\-\|:]+\|\s*$[\r\n]+(?:^\|.*\|\s*$[\r\n]+)+',
            # More flexible pattern for tables with simple format
            r'(?:^\|.*\|.*$[\r\n]*)+',  # At least 2 lines with pipes
            # Catch-all for any text that looks like it might contain table rows
            r'(?:\|[^\n]*\|[\r\n]*)+',  # Multiple lines with pipes
        ]

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if self.encoding is None:
            # Fallback character-based approximation
            return len(text) // 4
        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"Token counting failed: {e}, using approximation")
            return len(text) // 4

    def estimate_cost(self, text: str, cost_per_1000_tokens: float = 0.00002) -> float:
        """
        Estimate cost of processing text based on token count.

        Args:
            text: Text to estimate cost for
            cost_per_1000_tokens: Cost per 1000 tokens in USD

        Returns:
            Estimated cost in USD
        """
        token_count = self.count_tokens(text)
        return (token_count / 1000) * cost_per_1000_tokens

    def _find_tables(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Find all tables in the text and return their positions.

        Args:
            text: Input text containing potential tables

        Returns:
            List of tuples: (start_pos, end_pos, table_content)
        """
        tables = []

        for i, pattern in enumerate(self.table_patterns):
            matches = list(re.finditer(pattern, text, re.DOTALL | re.IGNORECASE | re.MULTILINE))
            logger.debug(f"Pattern {i+1} found {len(matches)} matches")
            for match in matches:
                start, end = match.span()
                table_content = match.group()
                logger.debug(f"  Match at {start}-{end}: {repr(table_content[:100])}...")

                # Check if this table overlaps with previously found tables
                overlaps = False
                for existing_start, existing_end, _ in tables:
                    if (start < existing_end and end > existing_start):
                        overlaps = True
                        break

                if not overlaps:
                    tables.append((start, end, table_content))

        # Sort by position
        tables.sort(key=lambda x: x[0])
        logger.info(f"Total tables found: {len(tables)}")
        return tables

    def _split_text_around_tables(self, text: str) -> List[str]:
        """
        Split text into chunks while preserving table integrity and semantic context.

        Strategy: Keep tables with surrounding context for semantic preservation.
        Only tables themselves are never split - context may be split if needed.

        Args:
            text: Input text to split

        Returns:
            List of text chunks with preserved semantic context
        """
        # Find all tables with their positions
        all_tables = self._find_all_table_regions(text)

        if not all_tables:
            logger.info("No tables found, using standard chunking")
            return self._character_based_split(text)

        logger.info(f"Found {len(all_tables)} table regions for semantic splitting")

        chunks = []
        processed_pos = 0

        for table_start, table_end, table_content in all_tables:
            # Extract context around the table
            context_start, context_end, full_context = self._extract_context_window(
                text, table_start, table_end, self.context_window_tokens
            )

            # Process any text before this context window
            if context_start > processed_pos:
                pre_context_text = text[processed_pos:context_start].strip()
                if pre_context_text:
                    # Split pre-context text normally
                    pre_chunks = self._character_based_split(pre_context_text)
                    chunks.extend(pre_chunks)

            # Check if table + context fits in one chunk
            context_tokens = self.count_tokens(full_context)

            if context_tokens <= self.max_tokens:
                # Perfect! Table + context fits in one chunk - semantic relationship preserved
                chunks.append(full_context)
                logger.info(f"Created semantic chunk: table + {context_tokens - self._estimate_table_tokens_only(table_content)} context tokens")
            else:
                # Context is too large - split it while keeping table together
                logger.info(f"Context too large ({context_tokens} tokens), splitting around table")

                # Split carefully around the table
                context_chunks = self._split_context_with_table_intact(
                    full_context, table_start - context_start, table_end - context_start
                )
                chunks.extend(context_chunks)

            processed_pos = context_end

        # Process any remaining text after the last table
        if processed_pos < len(text):
            remaining_text = text[processed_pos:].strip()
            if remaining_text:
                remaining_chunks = self._character_based_split(remaining_text)
                chunks.extend(remaining_chunks)

        return chunks

    def _find_all_table_regions(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Find all table regions in the text with their exact boundaries.

        Returns:
            List of (start, end, content) tuples for each table
        """
        tables = []
        table_pattern = '|'.join(f'({pattern})' for pattern in self.table_patterns)
        pattern = f'({table_pattern})'

        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE | re.MULTILINE):
            start, end = match.span()
            table_content = match.group()

            # Avoid overlaps
            if not any(existing_start <= start < existing_end or
                      existing_start < end <= existing_end
                      for existing_start, existing_end, _ in tables):
                tables.append((start, end, table_content))

        return sorted(tables, key=lambda x: x[0])

    def _extract_context_window(self, text: str, table_start: int, table_end: int,
                               context_tokens: int) -> Tuple[int, int, str]:
        """
        Extract a context window around a table with approximately context_tokens tokens.

        Returns:
            (context_start, context_end, full_context_text)
        """
        # Convert token count to approximate character count
        context_chars = context_tokens * 4  # Rough approximation for context window

        # Extract context before table
        pre_start = max(0, table_start - context_chars)
        pre_text = text[pre_start:table_start]

        # Extract table
        table_text = text[table_start:table_end]

        # Extract context after table
        post_end = min(len(text), table_end + context_chars)
        post_text = text[table_end:post_end]

        # Combine for full context
        full_start = pre_start
        full_end = post_end
        full_context = pre_text + table_text + post_text

        return full_start, full_end, full_context

    def _estimate_table_tokens_only(self, table_content: str) -> int:
        """Estimate tokens for table content only (without context)."""
        return self.count_tokens(table_content)

    def _split_context_with_table_intact(self, context_text: str,
                                        table_rel_start: int, table_rel_end: int) -> List[str]:
        """
        Split context text while keeping the table itself intact.
        Table position is relative to context_text.

        Returns:
            List of chunks, each containing parts of the table's context
        """
        chunks = []
        remainder = context_text

        while remainder:
            # Find the table position in current remainder
            table_start_in_chunk = remainder.find(context_text[table_rel_start:table_rel_end])

            if table_start_in_chunk == -1:
                # Table not in this remainder, split normally
                if self.count_tokens(remainder) <= self.max_tokens:
                    chunks.append(remainder)
                    break
                else:
                    # Split normally since table is not here
                    chunk = self._split_at_token_limit(remainder)
                    chunks.append(chunk)
                    remainder = remainder[len(chunk):]
            else:
                # Table is in this remainder - ensure it's not split
                chunk_size_limit = self.max_tokens

                # If we can fit the table + some context
                table_end_in_chunk = table_start_in_chunk + len(context_text[table_rel_start:table_rel_end])

                # Try to include as much context as possible without exceeding limit
                potential_end = min(len(remainder), table_end_in_chunk + (chunk_size_limit // 2))

                potential_chunk = remainder[:potential_end]
                if self.count_tokens(potential_chunk) <= self.max_tokens:
                    chunks.append(potential_chunk)
                    remainder = remainder[potential_end:]
                else:
                    # Can't even fit the table with minimal context - split before it
                    pre_table_chunk = remainder[:table_start_in_chunk].strip()
                    if pre_table_chunk:
                        if self.count_tokens(pre_table_chunk) <= self.max_tokens:
                            chunks.append(pre_table_chunk)
                        else:
                            # Pre-table text is too large
                            pre_table_split = self._character_based_split(pre_table_chunk)
                            chunks.extend(pre_table_split)

                    # Keep some context with the table
                    remaining_after_table = remainder[table_end_in_chunk:]
                    if remaining_after_table:
                        # Take some post-table context
                        post_context_end = min(len(remaining_after_table),
                                             int(len(remaining_after_table) * 0.3))  # 30% of remaining
                        table_chunk = remainder[table_start_in_chunk:table_end_in_chunk + post_context_end]

                        if table_chunk:
                            chunks.append(table_chunk)
                            remainder = remaining_after_table[post_context_end:]
                        else:
                            remainder = remaining_after_table
                    else:
                        remainder = ""

        return [chunk for chunk in chunks if chunk.strip()]
    def _character_based_split(self, text: str) -> List[str]:
        """
        Smart splitting that uses character's token-aware approach.

        Args:
            text: Text to split into chunks

        Returns:
            List of text chunks within token limits
        """
        if not text.strip():
            return []

        # Use separators that are table-aware and content-preserving
        separators = ["\n\n## ", "\n\n### ", "\n\n", ". ", " "]

        chunks = []
        remaining_text = text
        chunk_id = 0

        while remaining_text.strip():
            # Find the best split point within token limits
            best_split_point = len(remaining_text)
            best_chunk = remaining_text

            # Try separators in order of preference
            for separator in separators:
                # Split on separator
                parts = remaining_text.split(separator, 1)
                if len(parts) == 2:
                    potential_chunk = parts[0] + separator
                    token_count = self.count_tokens(potential_chunk)

                    if token_count <= self.max_tokens:
                        # Check if this gives us a better chunk (closer to max_tokens)
                        if len(chunks) == 0 or token_count >= self.max_tokens * 0.8:  # At least 80% of limit
                            best_chunk = potential_chunk
                            best_split_point = len(potential_chunk)
                            break

            # If no good separator found, force split at token limit
            if self.count_tokens(best_chunk) > self.max_tokens:
                best_chunk = self._split_at_token_limit(remaining_text)

            chunks.append(best_chunk.strip())
            remaining_text = remaining_text[len(best_chunk):].strip()

            # Safety check to prevent infinite loops
            if len(remaining_text) >= len(text):
                logger.warning(f"Split loop detected, forcing cut at token limit")
                remainder_chunks = self._split_at_token_limit(remaining_text)
                chunks.extend(remainder_chunks)
                break

            chunk_id += 1
            if chunk_id > 1000:  # Emergency break
                logger.error("Too many chunks created, breaking")
                break

        return [chunk for chunk in chunks if chunk.strip()]

    def _split_at_token_limit(self, text: str) -> str:
        """
        Split text exactly at the token limit using tiktoken.

        Args:
            text: Text to split
            max_tokens: Maximum tokens allowed

        Returns:
            Text split at token boundary
        """
        if self.encoding is None or not text:
            return text[:self.max_tokens * 4]  # Character approximation

        try:
            tokens = self.encoding.encode(text)
            if len(tokens) <= self.max_tokens:
                return text

            # Decode back to text at token limit
            limited_tokens = tokens[:self.max_tokens]
            return self.encoding.decode(limited_tokens)
        except Exception as e:
            logger.warning(f"Token-based splitting failed: {e}, using approximation")
            return text[:self.max_tokens * 4]

    def _is_table(self, text: str) -> bool:
        """Check if text contains a table structure."""
        for pattern in self.table_patterns:
            if re.search(pattern, text, re.DOTALL | re.IGNORECASE):
                return True
        return False

    def _split_large_table(self, table_text: str) -> List[str]:
        """
        Split a large table into smaller chunks while preserving structure.

        Args:
            table_text: Large table content

        Returns:
            List of table chunks
        """
        # For Markdown tables, try to split by rows
        if '|' in table_text and '\n' in table_text:
            lines = table_text.split('\n')
            chunks = []
            current_chunk = []

            for line in lines:
                current_chunk.append(line)
                current_text = '\n'.join(current_chunk)
                tokens = self.count_tokens(current_text)

                if tokens >= self.max_tokens and len(current_chunk) > 3:  # Keep at least header + separator + 1 row
                    # Remove the last line to stay under limit
                    current_chunk.pop()
                    if current_chunk:
                        chunks.append('\n'.join(current_chunk))
                    # Start new chunk with overlap (keep header and separator)
                    current_chunk = lines[:2] if len(lines) >= 2 else [lines[0]]

            if current_chunk:
                chunks.append('\n'.join(current_chunk))

            return chunks

        # Fallback: use token-based splitting
        return self._character_based_split(table_text)

    def split_text(self, text: str) -> List[str]:
        """
        Main method to split text while preserving table integrity.

        Args:
            text: Input text to split

        Returns:
            List of text chunks
        """
        try:
            return self._split_text_around_tables(text)
        except Exception as e:
            logger.error(f"Error in table-aware splitting: {e}")
            # Fallback to character-based splitting
            return self._character_based_split(text)

    def split_text_with_metadata(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Split text and return chunks with metadata.

        Args:
            text: Input text to split
            metadata: Base metadata to attach to each chunk

        Returns:
            List of dicts with 'text' and 'metadata' keys
        """
        chunks = self.split_text(text)
        result = []

        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                'chunk_id': i,
                'has_table': self._is_table(chunk),
                'token_count': self.count_tokens(chunk)
            })
            result.append({
                'text': chunk,
                'metadata': chunk_metadata
            })

        return result
#!/usr/bin/env python3
"""
Test script for table-aware chunking functionality.
"""

from crm.utils.table_aware_splitter import TableAwareTextSplitter
from crm.utils.token_text_splitter import TikTokenTextSplitter


def test_table_chunking():
    """Test table-aware chunking with sample content containing tables."""

    # Sample text with a table
    sample_text = """
    # Document Analysis Report

    This document contains important data about our sales performance.

    ## Sales Data Table

    | Month | Revenue | Growth | Target |
    |-------|---------|--------|--------|
    | January | $50,000 | 5.2% | $45,000 |
    | February | $52,600 | 5.2% | $47,250 |
    | March | $55,356 | 5.2% | $49,638 |
    | April | $58,274 | 5.2% | $52,211 |
    | May | $61,368 | 5.2% | $54,949 |
    | June | $64,637 | 5.2% | $57,857 |
    | July | $68,089 | 5.2% | $60,940 |
    | August | $71,733 | 5.2% | $64,203 |
    | September | $75,570 | 5.2% | $67,650 |
    | October | $79,599 | 5.2% | $71,285 |
    | November | $83,831 | 5.2% | $75,112 |
    | December | $88,275 | 5.2% | $79,137 |

    ## Analysis

    The table above shows our monthly sales performance with consistent 5.2% growth rate.
    This growth pattern indicates strong market penetration and effective sales strategies.

    ## Additional Data

    | Category | Q1 | Q2 | Q3 | Q4 |
    |----------|----|----|----|----|
    | Products | 150| 180| 210| 240|
    | Services | 75 | 90 | 105| 120|
    | Support  | 25 | 30 | 35 | 40 |

    The quarterly breakdown shows increasing demand across all categories.
    """

    print("=== TABLE-AWARE CHUNKING TEST ===\n")

    # Test with table-aware splitter
    table_splitter = TableAwareTextSplitter(max_tokens=200, overlap_tokens=50)
    table_chunks = table_splitter.split_text(sample_text)

    print(f"Table-aware splitter created {len(table_chunks)} chunks:\n")

    for i, chunk in enumerate(table_chunks):
        token_count = table_splitter.count_tokens(chunk)
        has_table = table_splitter._is_table(chunk)
        print(f"Chunk {i+1} ({token_count} tokens, table: {has_table}):")
        print(f"  Preview: {chunk[:150].strip()}...")
        print()

    print("\n" + "="*50 + "\n")

    # Compare with regular token splitter
    regular_splitter = TikTokenTextSplitter(max_tokens=200, overlap_tokens=50)
    regular_chunks = regular_splitter.split_text(sample_text)

    print(f"Regular token splitter created {len(regular_chunks)} chunks:\n")

    for i, chunk in enumerate(regular_chunks):
        token_count = regular_splitter.count_tokens(chunk)
        has_table = table_splitter._is_table(chunk)  # Use same detection logic
        print(f"Chunk {i+1} ({token_count} tokens, table: {has_table}):")
        print(f"  Preview: {chunk[:150].strip()}...")
        print()

    print("\n" + "="*50)
    print("COMPARISON SUMMARY:")
    print(f"  Table-aware chunks: {len(table_chunks)}")
    print(f"  Regular chunks: {len(regular_chunks)}")
    print(f"  Tables preserved: {sum(1 for c in table_chunks if table_splitter._is_table(c))}")
    print(f"  Tables split: {sum(1 for c in regular_chunks if table_splitter._is_table(c))}")


def test_large_table():
    """Test handling of large tables that exceed token limits."""

    # Create a very large table
    large_table = "| Row | " + " | ".join([f"Col{i}" for i in range(20)]) + " |\n"
    large_table += "|-----|" + "|".join(["------" for _ in range(20)]) + "|\n"

    for i in range(50):  # 50 rows
        row_data = [f"Row{i}"] + [f"Data{i}_{j}" for j in range(20)]
        large_table += "| " + " | ".join(row_data) + " |\n"

def test_token_counting_and_costs():
    """Test precise token counting and cost estimation features."""

    print("\n=== TOKEN COUNTING & COST ESTIMATION TEST ===\n")

    # Test content with different text types
    simple_text = "This is a simple test sentence. It has multiple words for testing."
    table_content = """
    | Month | Revenue | Growth | Target |
    |-------|---------|--------|--------|
    | January | $50,000 | 5.2% | $45,000 |
    | February | $52,600 | 5.2% | $47,250 |
    """

    splitter = TableAwareTextSplitter(max_tokens=1000, overlap_tokens=200)

    # Test token counting
    simple_tokens = splitter.count_tokens(simple_text)
    table_tokens = splitter.count_tokens(table_content)

    print(f"Simple text tokens: {simple_tokens}")
    print(f"Table content tokens: {table_tokens}")

    # Test cost estimation
    simple_cost = splitter.estimate_cost(simple_text)
    table_cost = splitter.estimate_cost(table_content)
    combined_cost = splitter.estimate_cost(simple_text + table_content)

    print(".6f")
    print(".6f")
    print(".6f")

    # Test with different models (different pricing)
    openai_embed_cost = splitter.estimate_cost(simple_text, cost_per_1000_tokens=0.0001)  # $0.10 per 1K
    openai_generation_cost = splitter.estimate_cost(simple_text, cost_per_1000_tokens=0.008)  # $8 per 1K

    print(".6f")
    print(".6f")

    return True


if __name__ == "__main__":
    test_table_chunking()
    test_token_counting_and_costs()

if __name__ == "__main__":
    test_table_chunking()

    print("\n=== LARGE TABLE TEST ===\n")
    test_large_table()

    test_token_counting_and_costs()
#!/usr/bin/env python3
"""
Debug script for table regex patterns.
"""

import re

def test_table_regex():
    """Test table regex patterns."""

    # Test text with table
    test_text = """
## Sales Data Table

| Month | Revenue | Growth | Target |
|-------|---------|--------|--------|
| January | $50,000 | 5.2% | $45,000 |
| February | $52,600 | 5.2% | $47,250 |

## Analysis

This is analysis text.
"""

    print("Test text:")
    print(repr(test_text))
    print("\n" + "="*50)

    # Test patterns
    patterns = [
        # Standard Markdown table with headers and separator row
        r'\|[^\n]*\|[\s]*\n\|[\s\-\|:]+\|[\s]*\n(?:\|[^\n]*\|[\s]*\n)+',
        # Simple table without headers (just rows with pipes)
        r'\|[^\n]*\|[\s]*\n(?:\|[^\n]*\|[\s]*\n){2,}',
        # HTML table tags (fallback for converted content)
        r'<table[^>]*>.*?</table>',
        # Alternative pattern for tables with consistent pipe separators
        r'^\|.*\|\s*$[\r\n]+\|[\s\-\|:]+\|\s*$[\r\n]+(?:^\|.*\|\s*$[\r\n]+)+',
    ]

    for i, pattern in enumerate(patterns):
        print(f"\nPattern {i+1}: {pattern}")
        matches = list(re.finditer(pattern, test_text, re.MULTILINE | re.DOTALL))
        print(f"Matches found: {len(matches)}")
        for match in matches:
            print(f"  Match: {repr(match.group())}")

    # Test simpler pattern
    simple_pattern = r'\|.*\|[\s]*\n\|[\s\-\|:]+\|[\s]*\n(?:\|.*\|[\s]*\n)+'
    print(f"\nSimple pattern: {simple_pattern}")
    matches = list(re.finditer(simple_pattern, test_text, re.MULTILINE))
    print(f"Simple matches found: {len(matches)}")
    for match in matches:
        print(f"  Match: {repr(match.group())}")

if __name__ == "__main__":
    test_table_regex()
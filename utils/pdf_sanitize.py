"""PDF text sanitization utilities shared by PDF generators.

Removes control characters, stray bullet-only lines, leading bullet symbols,
collapses repeated whitespace, keeps line structure.
"""
from __future__ import annotations
import re

BULLET_CHARS = '•▪■□●◦'

def sanitize_text_block(text: str) -> str:
    if not text:
        return ''
    # Normalize newlines
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Remove zero width / control (except common whitespace)
    text = ''.join(ch for ch in text if (32 <= ord(ch) or ch in ('\n','\t')))
    cleaned_lines = []
    for raw in text.split('\n'):
        line = raw.strip()
        if not line:
            continue
        if all(c in BULLET_CHARS for c in line):
            continue
        line = re.sub(r'^[%s]+\s*' % re.escape(BULLET_CHARS), '', line)
        line = re.sub(r'\s{2,}', ' ', line)
        # Replace any remaining bullet-like characters inside the line with a simple hyphen
        # to avoid fallback square glyphs (tests forbid these glyphs appearing in extracted text)
        if any(c in line for c in BULLET_CHARS):
            trans = {ord(c): '-' for c in BULLET_CHARS}
            line = line.translate(trans)
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines).strip()

__all__ = ['sanitize_text_block', 'BULLET_CHARS']

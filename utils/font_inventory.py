"""Utility to list fonts actually used inside a generated PDF (heuristic).

Parses PDF content streams with pypdf and extracts /F<id> references, listing
font resource names. Useful for verifying embedding & fallback behavior.
"""
from __future__ import annotations
import os
from pypdf import PdfReader

def list_pdf_fonts(path: str) -> list[str]:
    fonts = set()
    if not os.path.exists(path):
        return []
    try:
        reader = PdfReader(path)
        for page in reader.pages:
            try:
                resources = page.get('/Resources') or {}
                font_dict = resources.get('/Font') or {}
                for k in font_dict.keys():
                    fonts.add(str(k))
            except Exception:
                continue
    except Exception:
        return []
    return sorted(fonts)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python -m utils.font_inventory <pdf_path>')
        raise SystemExit(1)
    fonts = list_pdf_fonts(sys.argv[1])
    print('\n'.join(fonts) or '(no fonts found)')

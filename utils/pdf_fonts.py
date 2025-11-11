"""Shared font fallback selection utilities for PDF generators."""
from __future__ import annotations
from config import Config
from utils.logging_config import get_logger

_font_logger = get_logger(__name__)

def select_font_for_text(base_font: str, text: str, registered_fonts=None) -> str:
    """Adaptive font selection for Thai & CJK content.

    Strategy:
      1. Detect Thai (U+0E00–U+0E7F) and CJK Unified Ideographs (U+4E00–U+9FFF) plus basic CJK punctuation (U+3000–U+303F).
      2. Reorder configured fallback list so fonts whose names imply coverage (cjk, chinese, sourcehan, sc, thai) are tried first.
      3. Return first registered match. Provide debug logs if PDF_FONT_DEBUG enabled.
    """
    try:
        if not text:
            return base_font
        has_thai = any('\u0E00' <= ch <= '\u0E7F' for ch in text)
        has_cjk = any('\u4e00' <= ch <= '\u9fff' for ch in text)
        if not has_cjk:
            # CJK punctuation block
            has_cjk = any('\u3000' <= ch <= '\u303F' for ch in text)
        if not (has_thai or has_cjk):
            return base_font
        from reportlab.pdfbase import pdfmetrics
        reg = set(registered_fonts or pdfmetrics.getRegisteredFontNames())
        fallbacks = list(getattr(Config, 'PDF_FALLBACK_FONTS', []))
        ordered = fallbacks
        if has_cjk:
            cjk_pref = [f for f in fallbacks if any(tag in f.lower() for tag in ['cjk','chinese','sourcehan','sc'])]
            # Avoid accidentally prioritizing Thai specific fonts before CJK
            others = [f for f in fallbacks if f not in cjk_pref]
            ordered = cjk_pref + others
        elif has_thai:
            thai_pref = [f for f in fallbacks if 'thai' in f.lower()]
            others = [f for f in fallbacks if f not in thai_pref]
            ordered = thai_pref + others
        for cand in ordered:
            if cand in reg:
                if getattr(Config, 'PDF_FONT_DEBUG', False):
                    _font_logger.debug("font-select cand=%s hit for snippet='%.30s'", cand, text)
                return cand
        if has_thai and 'NotoSansThai' in reg:
            if getattr(Config, 'PDF_FONT_DEBUG', False):
                _font_logger.debug("font-select fallback forced NotoSansThai for snippet='%.30s'", text)
            return 'NotoSansThai'
        if getattr(Config, 'PDF_FONT_DEBUG', False):
            _font_logger.debug("font-select no match; using base=%s snippet='%.30s'", base_font, text)
        return base_font
    except Exception:
        return base_font

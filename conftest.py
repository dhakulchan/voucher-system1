import os
import pytest
from config import Config


@pytest.fixture(autouse=False)
def pdf_flags(monkeypatch):
    """Fixture to toggle common PDF flags for deterministic output in tests."""
    original = {
        'PDF_ENABLE_QR': Config.PDF_ENABLE_QR,
        'PDF_TABLE_ZEBRA': Config.PDF_TABLE_ZEBRA,
        'PDF_TERMS_LIST_STYLE': Config.PDF_TERMS_LIST_STYLE,
    }
    monkeypatch.setenv('PDF_ENABLE_QR','false')
    Config.PDF_ENABLE_QR = False
    yield
    # restore
    Config.PDF_ENABLE_QR = original['PDF_ENABLE_QR']
    Config.PDF_TABLE_ZEBRA = original['PDF_TABLE_ZEBRA']
    Config.PDF_TERMS_LIST_STYLE = original['PDF_TERMS_LIST_STYLE']

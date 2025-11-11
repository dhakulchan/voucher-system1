"""Common formatting helpers so tests can validate logic without parsing PDFs."""
from typing import Union, Optional
from datetime import datetime
from config import Config


def format_amount(amount: Union[float, int, None], currency_code: Optional[str] = None) -> str:
    if amount is None:
        return ''
    code = currency_code or getattr(Config, 'CURRENCY_CODE', 'THB')
    # Convert to float if it's a string to avoid format error
    try:
        amount_float = float(amount)
        return f"{code} {amount_float:,.2f}"
    except (ValueError, TypeError):
        return f"{code} {amount}"


def format_created_date(dt: Optional[datetime]) -> str:
    if not dt:
        return '-'
    # Keep legacy pattern for now (dd.Mon.YYYY) to avoid test churn
    return dt.strftime('%d.%b.%Y')


__all__ = ['format_amount', 'format_created_date']

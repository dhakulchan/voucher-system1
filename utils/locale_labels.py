"""Centralized label definitions and lookup for multiple locales.

Add new keys here and reference via get_label(key, lang).
Only a minimal set is defined initially; missing keys fall back to key itself.
"""
from typing import Dict
from config import Config

_LABELS: Dict[str, Dict[str, str]] = {
    'en': {
        'party_name': 'Party Name',
        'reference': 'Reference',
        'booking_type': 'Booking Type',
        'create_date': 'Create Date',
        'traveling_period': 'Traveling Period',
        'customer': 'Customer',
        'pax': 'PAX',
        'service_detail': 'Service Detail / Itinerary',
        'payment_information': 'Payment Information',
        'total': 'Total',
        'special_requests': 'Special Requests',
        'terms_conditions': 'Terms & Conditions',
        'invoice_no': 'ARNO',
        'quote_no': 'QTNO',
    },
    'th': {
        'party_name': 'ชื่อผู้จอง',
        'reference': 'เลขอ้างอิง',
        'booking_type': 'ประเภทการจอง',
        'create_date': 'วันที่สร้าง',
        'traveling_period': 'ช่วงเดินทาง',
        'customer': 'ลูกค้า',
        'pax': 'จำนวนผู้เดินทาง',
        'service_detail': 'รายละเอียดบริการ / โปรแกรม',
        'payment_information': 'ข้อมูลการชำระเงิน',
        'total': 'รวม',
        'special_requests': 'คำขอพิเศษ',
        'terms_conditions': 'เงื่อนไข',
        'invoice_no': 'ARNO',  # keep codes same
        'quote_no': 'QTNO',
    },
}


def get_label(key: str, lang: str | None = None) -> str:
    lang = (lang or getattr(Config, 'DEFAULT_LANGUAGE', 'en')).lower()
    return _LABELS.get(lang, _LABELS['en']).get(key, _LABELS['en'].get(key, key))


__all__ = ['get_label']

from typing import Optional
from models.customer import Customer
from services.invoice_ninja import InvoiceNinjaService


def link_or_create_client_for_customer(customer: Customer) -> Optional[int]:
    """Utility to search Invoice Ninja by email and link, else create client.
    Returns the client_id or None.
    """
    inv = InvoiceNinjaService()
    if not (customer and customer.email):
        return None
    existing = inv.find_client_by_email(customer.email)
    if existing:
        return existing.get('id')
    created = inv.create_client(
        name=customer.name or customer.full_name or 'Customer',
        email=customer.email,
        phone=customer.phone,
        address=getattr(customer, 'address', None)
    )
    if created:
        return created.get('id')
    return None

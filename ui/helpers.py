from collections import OrderedDict
from datetime import datetime
from typing import Optional, Sequence, Tuple

from flask import url_for

NavDefinition = Tuple[str, str, str, dict]

PRIMARY_NAV: Tuple[NavDefinition, ...] = (
    ('overview', 'Overview', 'index', {}),
    ('assistant', 'Assistant', 'assistant.assistant_dashboard', {}),
    ('contacts', 'Contacts', 'view_xero_contacts', {}),
    ('invoices', 'Invoices', 'view_xero_invoices', {}),
    ('setup', 'Setup', 'setup_wizard', {}),
    ('health', 'Health', 'health_check', {}),
    ('admin', 'Admin', 'admin_dashboard', {}),
)

def build_nav(active: str = 'overview', extras: Optional[Sequence[NavDefinition]] = None) -> list:
    """Return navigation items with the requested item marked as active."""
    nav_definitions: OrderedDict[str, NavDefinition] = OrderedDict()
    for identifier, label, endpoint, params in PRIMARY_NAV:
        nav_definitions[identifier] = (identifier, label, endpoint, params)

    if extras:
        for definition in extras:
            if not definition:
                continue
            identifier, label, endpoint, params = definition
            nav_definitions[identifier] = (identifier, label, endpoint, params)

    items: list[dict] = []
    for identifier, label, endpoint, params in nav_definitions.values():
        try:
            href = url_for(endpoint, **(params or {}))
        except Exception:
            continue
        items.append({
            'label': label,
            'href': href,
            'active': identifier == active,
        })
    return items

def format_timestamp(value: Optional[str], *, default: Optional[str] = None) -> Optional[str]:
    """Return a human friendly timestamp or a default fallback."""
    if not value:
        return default
    try:
        dt = datetime.fromisoformat(value)
    except Exception:
        return value
    return dt.strftime('%b %d, %Y %I:%M %p')

def summarize_details(details: Optional[dict]) -> str:
    """Convert a details dictionary into a compact printable string."""
    if not details:
        return ''
    if isinstance(details, dict):
        parts = [f"{key}: {value}" for key, value in details.items()]
        return '; '.join(parts)
    return str(details)

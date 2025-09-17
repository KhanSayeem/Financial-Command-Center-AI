from datetime import datetime
from typing import Iterable, Optional, Sequence, Tuple

from flask import url_for

NavDefinition = Tuple[str, str, str, dict]

def build_nav(active: str = 'overview', extras: Optional[Sequence[NavDefinition]] = None) -> list:
    """Return navigation items with the requested item marked as active."""
    base: list[NavDefinition] = [
        ('overview', 'Overview', 'index', {}),
        ('health', 'Health', 'health_check', {}),
        ('admin', 'Admin', 'admin_dashboard', {}),
    ]
    if extras:
        base.extend(extras)

    items: list[dict] = []
    for identifier, label, endpoint, params in base:
        try:
            href = url_for(endpoint, **params)
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

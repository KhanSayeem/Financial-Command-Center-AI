from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .helpers import format_timestamp, summarize_details

@dataclass
class AdminDashboardContext:
    stats: List[Dict[str, Any]]
    api_keys: List[Dict[str, Any]]
    recent_events: List[Dict[str, Any]]
    quick_links: List[Dict[str, Any]]
    mode_label: str
    security_enabled: bool


def build_admin_dashboard_context(security_enabled: bool, security_manager: Optional[Any], demo_manager: Any) -> AdminDashboardContext:
    api_keys_list: List[Dict[str, Any]] = []
    recent_events: List[Dict[str, Any]] = []
    total_keys = 0
    active_keys = 0
    unique_clients = 0

    if security_enabled and security_manager is not None:
        key_store = security_manager._load_json(security_manager.auth_file)
        audit_log = security_manager._load_json(security_manager.audit_file)

        total_keys = len(key_store)
        active_keys = sum(1 for info in key_store.values() if info.get('active'))
        unique_clients = len({info.get('client_name') for info in key_store.values() if info.get('client_name')})

        sorted_keys = sorted(
            key_store.items(),
            key=lambda item: item[1].get('created_at') or '',
            reverse=True,
        )
        for api_key, info in sorted_keys:
            mask = api_key if len(api_key) <= 12 else f"{api_key[:6]}...{api_key[-4:]}"
            api_keys_list.append({
                'id': api_key,
                'mask': mask,
                'client_name': info.get('client_name', 'Unknown client'),
                'active': bool(info.get('active', False)),
                'created_at': format_timestamp(info.get('created_at'), default='unknown'),
                'last_used': format_timestamp(info.get('last_used'), default='never'),
                'permissions': info.get('permissions', []),
                'daily_limit': info.get('daily_limit'),
                'monthly_limit': info.get('monthly_limit'),
            })

        events = audit_log.get('events', []) if isinstance(audit_log, dict) else []
        tone_map = {
            'invalid': 'danger',
            'error': 'danger',
            'rate_limit': 'warning',
            'warning': 'warning',
            'created': 'success',
        }
        for raw_event in list(events)[-10:][::-1]:
            event_label = str(raw_event.get('event_type', '')).replace('_', ' ').title()
            tone_key = next((key for key, _ in tone_map.items() if key in event_label.lower()), None)
            recent_events.append({
                'timestamp': format_timestamp(raw_event.get('timestamp'), default='unknown'),
                'event_type': event_label,
                'client_name': raw_event.get('client_name', 'Unknown client'),
                'details': summarize_details(raw_event.get('details')),
                'tone': tone_map.get(tone_key, 'info'),
            })

    stats = [
        {'label': 'Total API keys', 'value': total_keys, 'icon': 'key'},
        {'label': 'Active keys', 'value': active_keys, 'icon': 'check-circle', 'tone': 'success'},
        {'label': 'Unique clients', 'value': unique_clients, 'icon': 'users'},
        {'label': 'Audit events', 'value': len(recent_events), 'icon': 'history', 'tone': 'info'},
    ]

    quick_links = [
        {
            'label': 'Configure Claude Desktop',
            'description': 'Connect Claude to your financial cockpit.',
            'href': '/claude/setup',
            'icon': 'bot',
        },
        {
            'label': 'Configure Warp Terminal',
            'description': 'Drive compliance MCP commands from Warp.',
            'href': '/warp/setup',
            'icon': 'terminal',
        },
        {
            'label': 'Connect with ChatGPT',
            'description': 'Enable natural language financial commands.',
            'href': '/chatgpt/setup',
            'icon': 'bot',
        },
        {
            'label': 'Mode settings',
            'description': 'Switch between demo and live data.',
            'href': '/admin/mode',
            'icon': 'git-branch',
        },
        {
            'label': 'SSL help center',
            'description': 'Keep local certificates trusted for demos.',
            'href': '/admin/ssl-help',
            'icon': 'shield',
        },
        {
            'label': 'Download certificate bundle',
            'description': 'Install trusted roots on client machines.',
            'href': '/admin/certificate-bundle',
            'icon': 'download',
        },
    ]

    mode_label = 'Demo mode' if demo_manager.is_demo else 'Live mode'

    return AdminDashboardContext(
        stats=stats,
        api_keys=api_keys_list,
        recent_events=recent_events,
        quick_links=quick_links,
        mode_label=mode_label,
        security_enabled=security_enabled,
    )

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from flask import render_template, request

from .helpers import build_nav

def render_health_dashboard(health_data: Dict[str, Any], *, security_enabled: bool, session_config: Optional[Any]) -> str:
    nav_items = build_nav(
        'health',
        extras=[
            ('contacts', 'Contacts', 'view_xero_contacts', {}),
            ('invoices', 'Invoices', 'view_xero_invoices', {}),
            ('setup', 'Setup', 'setup_wizard', {}),
        ]
    )

    status_map = {
        'healthy': {
            'label': 'Operational',
            'message': 'All services are responding normally.',
            'icon': 'heart-pulse',
            'tone': 'success',
        },
        'warning': {
            'label': 'Attention needed',
            'message': 'Some services reported warnings. Review the details below.',
            'icon': 'alert-triangle',
            'tone': 'warning',
        },
        'error': {
            'label': 'Service disruption',
            'message': 'Critical issues detected. Investigate immediately.',
            'icon': 'octagon-alert',
            'tone': 'danger',
        },
    }

    status = status_map.get(health_data.get('status'), status_map['healthy'])

    timestamp = health_data.get('timestamp')
    observed_display = timestamp
    if timestamp:
        try:
            observed_display = _format_timestamp(timestamp)
        except Exception:
            observed_display = timestamp

    mode_value = health_data.get('mode', 'demo')
    mode_label = 'Demo data' if mode_value == 'demo' else 'Live data'
    security_flag = health_data.get('security') == 'enabled'

    metrics = [
        {
            'label': 'Operating mode',
            'value': mode_label,
            'description': 'Switch between demo and production in the admin area.',
            'icon': 'sparkles' if mode_value == 'demo' else 'shield-check',
            'tone': 'warning' if mode_value == 'demo' else 'success',
        },
        {
            'label': 'Security layer',
            'value': 'Enabled' if security_flag or security_enabled else 'Disabled',
            'description': 'API key enforcement and audit logging protect sensitive endpoints.' if security_flag or security_enabled else 'Install auth/security.py to enable API key enforcement.',
            'icon': 'shield',
            'tone': 'success' if security_flag or security_enabled else 'danger',
            'meta': ['Audit logging', 'Rate limits'] if security_flag or security_enabled else ['Configuration required'],
        },
        {
            'label': 'Connected services',
            'value': 'Stripe | Plaid | Xero',
            'description': 'Pre-wired connectors ready for show-time demos.',
            'icon': 'layers',
            'tone': 'info',
        },
    ]

    session_info = health_data.get('session_config') or {}
    session_card = _build_session_card(session_info, session_config)
    certificate = _build_certificate_card()
    integration_cards = _build_integration_cards(health_data.get('integrations') or {})

    health_json = json.dumps(health_data, indent=2, sort_keys=True)

    return render_template(
        'health.html',
        nav_items=nav_items,
        status=status,
        metrics=metrics,
        mode_label=mode_label,
        security_enabled=security_flag or security_enabled,
        observed_display=observed_display,
        request_host=request.host,
        session_card=session_card,
        certificate=certificate,
        integration_cards=integration_cards,
        health_data=health_data,
        health_json=health_json,
    )

def _format_timestamp(value: str) -> str:
    from datetime import datetime

    return datetime.fromisoformat(value).strftime('%b %d, %Y %I:%M %p')

def _build_session_card(session_info: Dict[str, Any], session_config: Optional[Any]) -> Dict[str, Any]:
    details = []
    for key, label in (
        ('status', 'Status'),
        ('backend', 'Backend'),
        ('storage_path', 'Storage path'),
        ('interface', 'Interface'),
        ('timeout', 'Timeout (s)'),
    ):
        if key in session_info and session_info[key] not in (None, ''):
            value = session_info[key]
            if key == 'timeout' and isinstance(value, (int, float)):
                value = f"{int(value)} s"
            details.append({'label': label, 'value': value})

    actions = []
    if session_config and getattr(session_config, 'debug_endpoint', None):
        actions.append({'label': 'Inspect session data', 'href': session_config.debug_endpoint, 'icon': 'bug'})

    return {
        'backend': session_info.get('backend'),
        'summary': (session_info.get('status') or 'Not configured').title() if session_info else 'Not configured',
        'message': session_info.get('message') or 'Flask session settings and storage health.',
        'details': details,
        'actions': actions,
    }

def _build_certificate_card() -> Dict[str, Any]:
    certificate = {
        'status_label': 'Manual review',
        'message': 'SSL management not available.',
        'summary': 'Not detected',
        'details': [],
    }
    try:
        from cert_manager import CertificateManager

        cert_manager = CertificateManager()
        cert_health = cert_manager.health_check()
        if cert_health:
            valid = bool(cert_health.get('certificate_valid'))
            expires = cert_health.get('expires') or 'unknown'
            hosts = ', '.join(cert_health.get('hostnames', [])) or 'localhost'
            certificate['status_label'] = 'Valid' if valid else 'Attention'
            certificate['message'] = 'Trusted certificates are ready for local HTTPS.' if valid else 'Certificates will regenerate automatically at launch.'
            certificate['summary'] = f"Valid until {expires}"
            certificate['details'] = [
                f"Valid: {'Yes' if valid else 'No'}",
                f"Hosts: {hosts}",
            ]
            if cert_health.get('last_renewed'):
                certificate['details'].append(f"Last renewed: {cert_health['last_renewed']}")
    except Exception:
        pass
    return certificate

def _build_integration_cards(integration_info: Dict[str, Any]) -> list:
    badge_classes = {
        'success': 'text-emerald-600',
        'warning': 'text-amber-600',
        'danger': 'text-rose-600',
        'info': 'text-sky-600',
    }
    integration_descriptions = {
        'xero': 'Invoices, contacts, and financial reports.',
        'stripe': 'Payments, subscriptions, and billing flows.',
        'plaid': 'Banking connections and transaction monitoring.',
    }

    cards = []
    for key, value in integration_info.items():
        name = key.replace('_', ' ').title()
        normalized = str(value).lower()
        if normalized in {'configured', 'connected', 'available', 'ready'}:
            tone = 'success'
            status_label = 'Configured'
            icon = 'check'
        elif normalized in {'demo', 'optional'}:
            tone = 'info'
            status_label = normalized.title()
            icon = 'sparkles'
        elif normalized in {'warning', 'degraded', 'pending'}:
            tone = 'warning'
            status_label = normalized.title()
            icon = 'alert-triangle'
        else:
            tone = 'danger'
            status_label = normalized.title() if normalized else 'Unavailable'
            icon = 'x-circle'

        cards.append({
            'category': 'Integration',
            'title': name,
            'status_label': status_label,
            'icon': icon,
            'badge_class': badge_classes.get(tone, 'text-muted-foreground'),
            'description': integration_descriptions.get(key, ''),
            'details': [],
        })
    return cards

import os
from flask import render_template

from ui.helpers import build_nav

def setup_claude_routes(app, logger=None):
    """Setup Claude Desktop integration routes on the Flask app."""

    @app.route('/claude/setup')
    def claude_setup_page():
        port = app.config.get('PORT', int(os.getenv('FCC_PORT', '8000')))
        server_url = f"https://localhost:{port}"
        if logger:
            logger.info("Serving Claude Desktop setup instructions")

        nav_items = build_nav(
            'setup',
            extras=[
                ('overview', 'Overview', 'index', {}),
                ('contacts', 'Contacts', 'view_xero_contacts', {}),
                ('invoices', 'Invoices', 'view_xero_invoices', {}),
            ],
        )

        return render_template(
            'integrations/claude_setup.html',
            server_url=server_url,
            nav_items=nav_items,
        )


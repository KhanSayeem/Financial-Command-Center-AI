import os
from flask import render_template

from ui.helpers import build_nav

def setup_warp_routes(app, logger=None):
    """Setup Warp AI Terminal integration routes on the Flask app."""

    @app.route('/warp/setup')
    def warp_setup_page():
        port = app.config.get('PORT', int(os.getenv('FCC_PORT', '8000')))
        server_url = f"https://localhost:{port}"
        if logger:
            logger.info("Serving Warp Terminal setup instructions")

        nav_items = build_nav(
            'setup',
            extras=[
                ('overview', 'Overview', 'index', {}),
                ('contacts', 'Contacts', 'view_xero_contacts', {}),
                ('invoices', 'Invoices', 'view_xero_invoices', {}),
            ],
        )

        return render_template(
            'integrations/warp_setup.html',
            server_url=server_url,
            nav_items=nav_items,
        )


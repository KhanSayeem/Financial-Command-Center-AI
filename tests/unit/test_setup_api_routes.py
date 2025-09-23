import json
import logging
from unittest.mock import MagicMock

import pytest
from flask import Flask

from setup_api_routes import create_setup_blueprint


@pytest.fixture()
def setup_api_client():
    app = Flask(__name__)
    app.config.update(TESTING=True)

    setup_wizard_api = MagicMock()
    setup_wizard_api.test_stripe_connection.return_value = {'success': True}
    setup_wizard_api.test_xero_connection.return_value = {'success': True}
    setup_wizard_api.test_plaid_connection.return_value = {'success': True}
    setup_wizard_api.save_configuration.return_value = {'success': True}
    setup_wizard_api.get_configuration_status.return_value = {'configured': False}

    post_save_callback = MagicMock()
    connection_status_provider = MagicMock(return_value={
        'connected': True,
        'tenant_id': 'tenant-123',
        'has_token': True,
    })

    logger = logging.getLogger('setup-api-test')

    blueprint = create_setup_blueprint(
        setup_wizard_api=setup_wizard_api,
        logger=logger,
        post_save_callback=post_save_callback,
        connection_status_provider=connection_status_provider,
    )
    app.register_blueprint(blueprint, url_prefix='/api/setup')

    with app.test_client() as client:
        yield client, setup_wizard_api, post_save_callback, connection_status_provider


def test_setup_status_endpoint_returns_configuration(setup_api_client):
    client, setup_wizard_api, *_ = setup_api_client

    response = client.get('/api/setup/status')
    data = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert data == setup_wizard_api.get_configuration_status.return_value
    setup_wizard_api.get_configuration_status.assert_called_once_with()


def test_save_config_invokes_post_save_on_success(setup_api_client):
    client, setup_wizard_api, post_save_callback, _ = setup_api_client

    payload = {'stripe': {'skipped': True}}
    response = client.post('/api/setup/save-config', data=json.dumps(payload), content_type='application/json')
    data = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert data['success'] is True
    post_save_callback.assert_called_once()
    setup_wizard_api.save_configuration.assert_called_once_with(payload)


def test_save_config_rejects_missing_payload(setup_api_client):
    client, setup_wizard_api, post_save_callback, _ = setup_api_client

    response = client.post('/api/setup/save-config', data='{}', content_type='application/json')

    assert response.status_code == 400
    post_save_callback.assert_not_called()
    setup_wizard_api.save_configuration.assert_not_called()


def test_xero_connection_endpoint_uses_provider(setup_api_client):
    client, _, __, connection_status_provider = setup_api_client

    response = client.get('/api/setup/xero-connection')
    data = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 200
    assert data['connected'] is True
    assert data['tenant_id'] == 'tenant-123'
    connection_status_provider.assert_called_once_with()


def test_xero_connection_endpoint_handles_errors(setup_api_client):
    client, _, __, connection_status_provider = setup_api_client
    connection_status_provider.side_effect = RuntimeError('boom')

    response = client.get('/api/setup/xero-connection')
    data = json.loads(response.data.decode('utf-8'))

    assert response.status_code == 500
    assert data['connected'] is False
    assert 'error' in data


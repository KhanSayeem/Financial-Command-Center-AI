import pytest

from setup_wizard import (
    stage_service_credentials,
    get_staged_credentials,
    clear_staged_credentials,
)


@pytest.fixture(autouse=True)
def reset_staging_state():
    """Ensure each test starts with a clean staging cache."""
    clear_staged_credentials()
    yield
    clear_staged_credentials()


def test_stage_and_fetch_xero_credentials():
    staged = stage_service_credentials('xero', {
        'client_id': 'client-123',
        'client_secret': 'secret-abc',
    })

    assert staged['client_id'] == 'client-123'
    assert staged['client_secret'] == 'secret-abc'

    retrieved = get_staged_credentials('xero')
    assert retrieved == staged


def test_staging_clears_when_payload_empty():
    stage_service_credentials('xero', {
        'client_id': 'client-123',
        'client_secret': 'secret-abc',
    })
    assert get_staged_credentials('xero')

    stage_service_credentials('xero', {})
    assert get_staged_credentials('xero') == {}


def test_clear_specific_service_only_removes_target():
    stage_service_credentials('xero', {
        'client_id': 'client-123',
        'client_secret': 'secret-abc',
    })
    stage_service_credentials('plaid', {
        'client_id': 'plaid-123',
    })

    clear_staged_credentials('xero')

    assert get_staged_credentials('xero') == {}
    assert get_staged_credentials('plaid')['client_id'] == 'plaid-123'

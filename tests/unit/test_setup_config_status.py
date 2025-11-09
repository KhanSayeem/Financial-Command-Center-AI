import datetime

from setup_wizard import ConfigurationManager, SetupWizardAPI


def test_configuration_status_requires_configured_at(tmp_path):
    config_dir = tmp_path / "secure_config"
    cm = ConfigurationManager(config_dir=str(config_dir))
    cm.save_config({
        'stripe': {
            'api_key': 'sk_test_seeded'
        },
        'xero': {
            'client_id': 'client',
            'client_secret': 'secret',
            'configured_at': datetime.datetime.now().isoformat()
        }
    })

    status = cm.get_configuration_status()

    assert status['services']['stripe']['has_credentials'] is True
    assert status['services']['stripe']['configured'] is False
    assert status['services']['xero']['configured'] is True
    assert status['configured'] is False


def test_save_configuration_merges_existing_service_data():
    api = SetupWizardAPI()

    class DummyManager:
        def __init__(self):
            self.saved_config = None

        def load_config(self):
            return {
                'stripe': {
                    'client_id': 'cid_123',
                    'redirect_uri': 'https://localhost/oauth/stripe'
                }
            }

        def save_config(self, config):
            self.saved_config = config
            return True

    dummy_manager = DummyManager()
    api.config_manager = dummy_manager

    payload = {
        'stripe': {
            'api_key': 'sk_test_new',
            'publishable_key': 'pk_test_new'
        }
    }

    result = api.save_configuration(payload)

    assert result['success'] is True
    assert 'stripe' in dummy_manager.saved_config
    assert dummy_manager.saved_config['stripe']['client_id'] == 'cid_123'
    assert dummy_manager.saved_config['stripe']['api_key'] == 'sk_test_new'
    assert 'configured_at' in dummy_manager.saved_config['stripe']

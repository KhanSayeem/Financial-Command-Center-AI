from flask import Blueprint, jsonify, request


def create_setup_blueprint(*, setup_wizard_api, logger, post_save_callback, connection_status_provider,
                           stripe_status_provider=None, plaid_status_provider=None,
                           blueprint_name: str = 'setup_api'):
    """Return a blueprint that exposes the setup API endpoints."""

    bp = Blueprint(blueprint_name, __name__)

    @bp.route('/test-stripe', methods=['POST'])
    def test_stripe_api():
        data = request.get_json() or {}
        result = setup_wizard_api.test_stripe_connection(data)
        return jsonify(result)

    @bp.route('/test-xero', methods=['POST'])
    def test_xero_api():
        data = request.get_json() or {}
        result = setup_wizard_api.test_xero_connection(data)
        return jsonify(result)

    @bp.route('/test-plaid', methods=['POST'])
    def test_plaid_api():
        data = request.get_json() or {}
        result = setup_wizard_api.test_plaid_connection(data)
        return jsonify(result)

    @bp.route('/save-config', methods=['POST'])
    def save_setup_config():
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            result = setup_wizard_api.save_configuration(data)

            if result.get('success'):
                try:
                    post_save_callback(result)
                except Exception as callback_error:  # pragma: no cover - defensive logging
                    logger.error(f'Post-save setup hook failed: {callback_error}')
                    warnings = result.setdefault('warnings', [])
                    warnings.append(f'Post-save hook error: {callback_error}')

            return jsonify(result)
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.error(f'Error saving configuration: {exc}')
            return jsonify({'success': False, 'error': str(exc)}), 500

    @bp.route('/status', methods=['GET'])
    def get_setup_status():
        result = setup_wizard_api.get_configuration_status()
        return jsonify(result)

    @bp.route('/xero-connection', methods=['GET'])
    def get_xero_connection_status():
        try:
            payload = connection_status_provider() or {}
            status_code = payload.pop('status_code', 200)
            return jsonify(payload), status_code
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(f'Failed to read Xero connection status: {exc}')
            return jsonify({
                'connected': False,
                'tenant_id': '',
                'has_token': False,
                'error': str(exc),
            }), 500

    if stripe_status_provider:
        @bp.route('/stripe-connection', methods=['GET'])
        def get_stripe_connection_status():
            try:
                payload = stripe_status_provider() or {}
                status_code = payload.pop('status_code', 200)
                return jsonify(payload), status_code
            except Exception as exc:  # pragma: no cover
                logger.error(f'Failed to read Stripe connection status: {exc}')
                return jsonify({
                    'connected': False,
                    'account_id': '',
                    'error': str(exc),
                }), 500

    if plaid_status_provider:
        @bp.route('/plaid-connection', methods=['GET'])
        def get_plaid_connection_status():
            try:
                payload = plaid_status_provider() or {}
                status_code = payload.pop('status_code', 200)
                return jsonify(payload), status_code
            except Exception as exc:  # pragma: no cover
                logger.error(f'Failed to read Plaid connection status: {exc}')
                return jsonify({
                    'connected': False,
                    'item_id': '',
                    'error': str(exc),
                }), 500

    @bp.route('/debug-config', methods=['GET'])
    def debug_config():
        """Debug endpoint to check current configuration"""
        try:
            from setup_wizard import ConfigurationManager
            cm = ConfigurationManager()
            config = cm.load_config() or {}

            return jsonify({
                'success': True,
                'config': config,
                'file_exists': cm.config_file.exists(),
                'file_path': str(cm.config_file)
            })
        except Exception as exc:
            return jsonify({
                'success': False,
                'error': str(exc)
            }), 500

    @bp.route('/force-config', methods=['POST'])
    def force_config():
        """Debug endpoint to manually set configuration"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            from setup_wizard import ConfigurationManager
            cm = ConfigurationManager()
            success = cm.save_config(data)

            return jsonify({
                'success': success,
                'message': 'Configuration forcefully saved' if success else 'Failed to save configuration'
            })
        except Exception as exc:
            return jsonify({
                'success': False,
                'error': str(exc)
            }), 500

    return bp


import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from flask import jsonify, render_template, request

from ui.helpers import build_nav
from setup_wizard import get_integration_status

try:
    from auth.security import SecurityManager
except Exception:  # pragma: no cover - optional dependency
    SecurityManager = None  # type: ignore[assignment]

def setup_claude_routes(app, logger=None):
    """Setup Claude Desktop integration routes on the Flask app."""

    @app.route('/claude/setup')
    def claude_setup_page():
        port = app.config.get('PORT', int(os.getenv('FCC_PORT', '8000')))
        server_url = f"https://localhost:{port}"
        nav_items = build_nav('setup')

        return render_template(
            'integrations/claude_setup.html',
            server_url=server_url,
            nav_items=nav_items,
        )

    @app.route('/api/claude/generate-config', methods=['GET'])
    def generate_claude_config():
        try:
            import time
            # Small delay to ensure any concurrent save operations have completed
            time.sleep(0.1)

            config_json, summary, server_url = _build_claude_config(app)
            summary['integration_status'] = get_integration_status()
            return jsonify({
                'success': True,
                'config': config_json,
                'summary': summary,
                'server_url': server_url,
                'message': f"Configuration generated with {summary['total_servers']} MCP servers",
                'timestamp': time.time()  # Add timestamp for debugging
            })
        except Exception as exc:
            if logger:
                logger.error(f"Claude config generation error: {exc}")
            return jsonify({
                'success': False,
                'message': f"Configuration generation error: {exc}",
            }), 500

    @app.route('/api/claude/config-path', methods=['GET'])
    def claude_config_path_status():
        try:
            status = _get_claude_config_status()
            return jsonify({'success': True, 'status': status})
        except Exception as exc:  # pragma: no cover - defensive
            if logger:
                logger.error(f"Claude config path status error: {exc}")
            return jsonify({'success': False, 'message': str(exc)}), 500

    @app.route('/api/claude/connect', methods=['POST'])
    def claude_connect_now():
        try:
            config_json, summary, _ = _build_claude_config(app)
            target_path = _resolve_claude_config_path()
            write_result = _write_claude_config_file(config_json, target_path)
            status = _get_claude_config_status(target_path)
            _log_claude_security_event(
                'claude_config_updated',
                {
                    'path': status.get('path'),
                    'backup_path': write_result.get('backup_path'),
                    'bytes_written': write_result.get('bytes_written'),
                },
            )
            return jsonify({
                'success': True,
                'message': 'Claude Desktop configuration updated successfully.',
                'path': status.get('path'),
                'status': status,
                'summary': summary,
                'config': config_json,
                'backup_path': write_result.get('backup_path'),
            })
        except PermissionError as exc:
            if logger:
                logger.error(f"Claude config write permission error: {exc}")
            return jsonify({
                'success': False,
                'message': 'Permission denied while writing to Claude configuration.'
            }), 403
        except Exception as exc:  # pragma: no cover - defensive
            if logger:
                logger.error(f"Claude connect error: {exc}")
            return jsonify({'success': False, 'message': str(exc)}), 500

    @app.route('/api/claude/restore', methods=['POST'])
    def claude_restore_backup():
        data = request.get_json(silent=True) or {}
        backup_path_value = data.get('backup_path')
        if not backup_path_value:
            return jsonify({'success': False, 'message': 'Backup path is required.'}), 400

        try:
            target_path = _resolve_claude_config_path()
            backup_path = Path(backup_path_value).expanduser()
            _ensure_backup_within_target(backup_path, target_path)
            if not backup_path.exists():
                return jsonify({'success': False, 'message': 'Selected backup no longer exists.'}), 404

            config_json = backup_path.read_text(encoding='utf-8')
            write_result = _write_claude_config_file(config_json, target_path)
            status = _get_claude_config_status(target_path)
            _log_claude_security_event(
                'claude_config_restored',
                {
                    'restored_from': str(backup_path),
                    'path': status.get('path'),
                    'backup_path': write_result.get('backup_path'),
                },
            )
            return jsonify({
                'success': True,
                'message': 'Claude configuration restored from backup.',
                'path': status.get('path'),
                'status': status,
                'backup_path': write_result.get('backup_path'),
            })
        except PermissionError as exc:
            if logger:
                logger.error(f"Claude config restore permission error: {exc}")
            return jsonify({
                'success': False,
                'message': 'Permission denied while restoring Claude configuration.'
            }), 403
        except ValueError as exc:
            return jsonify({'success': False, 'message': str(exc)}), 400
        except Exception as exc:  # pragma: no cover - defensive
            if logger:
                logger.error(f"Claude restore error: {exc}")
            return jsonify({'success': False, 'message': str(exc)}), 500

    return True

def _build_claude_config(app) -> Tuple[str, Dict[str, object], str]:
    """Generate the Claude Desktop MCP configuration payload."""
    from setup_wizard import ConfigurationManager

    # Create a fresh ConfigurationManager instance to ensure we get the latest config
    config_manager = ConfigurationManager()

    # Force a fresh read by clearing any potential caches
    # Check if config file exists and force a fresh stat to avoid OS caching
    if config_manager.config_file.exists():
        # Touch the file access time to ensure fresh read
        import time
        config_manager.config_file.touch()

    stored_config = config_manager.load_config() or {}
    app.logger.info(f"Stored config: {stored_config}")

    # Debug logging to help identify issues
    if hasattr(app, 'logger') and app.logger:
        stripe_config = stored_config.get('stripe', {})
        if stripe_config and not stripe_config.get('skipped'):
            api_key = stripe_config.get('api_key', '')
            app.logger.info(f"Claude config generation using Stripe key: {api_key[:20]}..." if len(api_key) > 20 else f"Stripe key: {api_key}")
        else:
            app.logger.info("Claude config generation: No Stripe config found or skipped")

    port = app.config.get('PORT', int(os.getenv('FCC_PORT', '8000')))
    server_url = f"https://localhost:{port}"

    base_dir = Path(__file__).resolve().parent
    python_exe = _detect_python_executable(base_dir)

    mcp_servers: Dict[str, Dict[str, object]] = {}

    def _add_server(key: str, script_name: str, env: Dict[str, object]):
        script_path = base_dir / script_name
        if script_path.exists():
            mcp_servers[key] = {
                'command': python_exe,
                'args': [str(script_path)],
                'env': {k: v for k, v in env.items() if v},
            }

    integration_status = get_integration_status()

    _add_server(
        'financial-command-center',
        'mcp_server.py',
        {
            'FCC_SERVER_URL': server_url,
            'FCC_API_KEY': 'claude-desktop-integration',
        },
    )

    stripe_config = stored_config.get('stripe', {})
    if stripe_config and not stripe_config.get('skipped') and integration_status.get('stripe', {}).get('configured'):
        _add_server(
            'stripe-payments',
            'stripe_mcp.py',
            {
                'STRIPE_API_KEY': stripe_config.get('api_key'),
                'STRIPE_PUBLISHABLE_KEY': stripe_config.get('publishable_key', ''),
                'FCC_SYNC_ENDPOINT': '/sync/stripe',
            },
        )

    xero_config = stored_config.get('xero', {})
    if xero_config and not xero_config.get('skipped') and integration_status.get('xero', {}).get('configured'):
        _add_server(
            'xero-accounting',
            'xero_mcp.py',
            {
                'XERO_CLIENT_ID': xero_config.get('client_id'),
                'XERO_CLIENT_SECRET': xero_config.get('client_secret'),
                'FCC_SYNC_ENDPOINT': '/sync/xero',
            },
        )

    plaid_config = stored_config.get('plaid', {})
    if plaid_config and not plaid_config.get('skipped') and integration_status.get('plaid', {}).get('configured'):
        _add_server(
            'plaid-banking',
            'plaid_mcp.py',
            {
                'PLAID_CLIENT_ID': plaid_config.get('client_id'),
                'PLAID_SECRET': plaid_config.get('secret'),
                'PLAID_ENV': plaid_config.get('environment', 'sandbox'),
                'FCC_SYNC_ENDPOINT': '/sync/plaid',
            },
        )

    compliance_env: Dict[str, object] = {}
    if plaid_config and not plaid_config.get('skipped'):
        compliance_env.update({
            'PLAID_CLIENT_ID': plaid_config.get('client_id'),
            'PLAID_SECRET': plaid_config.get('secret'),
            'PLAID_ENV': plaid_config.get('environment', 'sandbox'),
        })
    if stripe_config and not stripe_config.get('skipped'):
        compliance_env['STRIPE_API_KEY'] = stripe_config.get('api_key')

    _add_server(
        'compliance-suite',
        'compliance_mcp.py',
        compliance_env,
    )

    automation_env = dict(compliance_env)
    _add_server(
        'automation-workflows',
        'automation_mcp.py',
        automation_env,
    )

    config_json = json.dumps({'mcpServers': mcp_servers}, indent=2)

    included_servers = list(mcp_servers.keys())
    setup_type = 'virtual_environment' if 'venv' in python_exe else 'system_python'

    summary = {
        'total_servers': len(included_servers),
        'servers': included_servers,
        'integrations': integration_status,
        'python_executable': python_exe,
        'project_directory': str(base_dir),
        'setup_type': setup_type,
        'portable_instructions': {
            'note': 'This configuration is customized for your specific setup',
            'python_location': 'Virtual environment detected' if 'venv' in python_exe else 'System Python detected',
            'paths_are_absolute': 'Paths are specific to your project directory',
            'sharing_note': 'Other users should generate their own config from their setup',
        },
    }

    return config_json, summary, server_url


def _resolve_claude_config_path() -> Path:
    """Return the platform-specific Claude Desktop config path."""
    home = Path.home()
    if sys.platform.startswith('win'):
        appdata = os.environ.get('APPDATA')
        base = Path(appdata) if appdata else home / 'AppData' / 'Roaming'
        target_dir = base / 'Claude'
    elif sys.platform == 'darwin':
        target_dir = home / 'Library' / 'Application Support' / 'Claude'
    else:
        xdg = os.environ.get('XDG_CONFIG_HOME')
        base = Path(xdg) if xdg else home / '.config'
        target_dir = base / 'Claude'

    return target_dir / 'claude_desktop_config.json'


def _get_claude_config_status(target_path: Optional[Path] = None) -> Dict[str, object]:
    """Return metadata about the Claude Desktop config file."""
    path = target_path or _resolve_claude_config_path()
    parent = path.parent
    exists = path.exists()
    status: Dict[str, object] = {
        'path': str(path),
        'directory_exists': parent.exists(),
        'exists': exists,
        'platform': sys.platform,
    }

    if exists:
        stat = path.stat()
        status['last_modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        status['bytes'] = stat.st_size
    else:
        status['last_modified'] = None
        status['bytes'] = 0

    status['backups'] = _list_claude_backups(path)
    return status


def _list_claude_backups(target_path: Path) -> List[Dict[str, object]]:
    """Return recent backup files for the Claude config."""
    parent = target_path.parent
    if not parent.exists():
        return []

    pattern = f"{target_path.stem}.backup-*.json"
    backups: List[Dict[str, object]] = []
    for candidate in sorted(parent.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            stat = candidate.stat()
            backups.append({
                'path': str(candidate),
                'label': candidate.name,
                'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'bytes': stat.st_size,
            })
        except OSError:
            continue
    return backups[:10]


def _write_claude_config_file(config_json: str, destination: Path) -> Dict[str, Optional[str]]:
    """Write the Claude config, creating a backup if a file already exists."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Optional[Path] = None

    if destination.exists():
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{destination.stem}.backup-{timestamp}{destination.suffix or '.json'}"
        backup_path = destination.with_name(backup_name)
        shutil.copy2(destination, backup_path)

    tmp_path = destination.with_name(f".{destination.name}.tmp")
    tmp_path.write_text(config_json, encoding='utf-8')
    os.replace(tmp_path, destination)

    return {
        'backup_path': str(backup_path) if backup_path else None,
        'bytes_written': len(config_json.encode('utf-8')),
    }


def _ensure_backup_within_target(backup_path: Path, target_path: Path) -> None:
    """Ensure the backup path lives inside Claude's config directory."""
    target_dir = target_path.parent
    resolved_backup = backup_path.resolve()
    resolved_dir = target_dir.resolve()
    try:
        resolved_backup.relative_to(resolved_dir)
    except ValueError:
        raise ValueError("Backup path must be within the Claude configuration directory.")


def _log_claude_security_event(event_type: str, details: Dict[str, object]) -> None:
    """Log actions to the security manager if available."""
    if not SecurityManager:
        return
    client_name = 'Claude Setup UI'
    try:
        info = getattr(request, 'client_info', None)
        if isinstance(info, dict):
            client_name = info.get('client_name', client_name)
    except RuntimeError:
        pass
    try:
        SecurityManager().log_security_event(event_type, client_name, details)
    except Exception:
        pass

def _detect_python_executable(base_dir: Path) -> str:
    """Return the best python executable path for the current environment."""
    import shutil

    candidates = [
        base_dir / '.venv' / 'Scripts' / 'python.exe',
        base_dir / '.venv' / 'bin' / 'python',
        base_dir / 'venv' / 'Scripts' / 'python.exe',
        base_dir / 'venv' / 'bin' / 'python',
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    for executable in ('python', 'python3'):
        resolved_path = shutil.which(executable)
        if resolved_path:
            return resolved_path

    return 'python'

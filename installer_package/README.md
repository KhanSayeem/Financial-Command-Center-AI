# Financial Command Center AI

## **NEW: Claude Desktop AI Integration**

Unified financial operations platform with one‑click launcher, HTTPS by default, setup wizard, and **Claude Desktop AI integration** for natural language financial operations!

**✨ AI Features:**
- Natural language commands: "Show cash flow", "List unpaid invoices", "Find contacts"
- Intelligent financial analysis and reporting
- Voice-activated operations through Claude Desktop
- System health monitoring via AI commands

This update makes installation reliable on Windows: dependencies install into a user‑writable venv, the launcher auto‑detects the app files, and the server comes up on an available port with SSL certificates generated automatically.

---

## Quick Start

- One‑click: run `installer_package\Financial-Command-Center-Launcher.exe`.
- From source: `python financial_launcher.py --setup`.

The launcher will:
- Create a venv at `%LOCALAPPDATA%\Financial Command Center\Python\.venv`.
- Install dependencies (with a resilient fallback for demo‑only mode).
- Generate SSL certificates and start the server.
- Open your browser to `https://localhost:8000` and add system‑tray shortcuts.

---

## Configuration

- `FCC_PORT`: preferred port (default `8000`; auto‑fallback to `8001–8010`).
- `FORCE_HTTPS=true`, `ALLOW_HTTP=false` for secure HTTPS by default.
- Optional live credentials:
  - `STRIPE_API_KEY`
  - `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`

The app runs fully in demo mode without real credentials.

---

## Troubleshooting

- Logs: `%LOCALAPPDATA%\Financial Command Center\Logs\launcher.log`.
- Dependency errors: the launcher logs full pip output and then retries with a minimal set to enable demo mode. Re‑run after fixing network or system prerequisites.
- Port in use: set `FCC_PORT` or close any previous instance bound to `:8000`.
- Certificate warnings: `python cert_manager.py --bundle`, then run `certs\client_bundle\install_certificate_windows.bat` as Administrator.

---

## Building the Launcher (for contributors)

```powershell
python build_launcher.py
```

Outputs:
- EXE: `dist/Financial-Command-Center-Launcher.exe`
- Distribution folder (EXE + app sources): `installer_package/`

---

## Key Endpoints

- Home/setup: `https://localhost:<port>/` and `/setup`
- **Claude AI Setup**: `https://localhost:<port>/claude/setup`
- Health: `https://localhost:<port>/health`
- Admin: `https://localhost:<port>/admin/dashboard`
- SSL help: `https://localhost:<port>/admin/ssl-help`

---

## Notes

The repo still includes MCP tooling for Stripe/Xero/Plaid; it works unchanged. The launcher and setup wizard focus on a secure, no‑friction local run experience.

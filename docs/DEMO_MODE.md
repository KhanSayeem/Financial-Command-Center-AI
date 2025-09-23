# Demo Mode (No API keys required)

Run the app instantly without real credentials using Demo Mode.

What’s included:

- Mock Stripe: Fake successful payments using PaymentIntent-like responses
- Mock Xero: Realistic sample contacts, invoices, and a simple P&L
- Mock Plaid: Sample business accounts and transactions
- UI Indicators: A banner shows Demo Mode and an “Upgrade to Real Data” CTA
- Mode Toggle: Switch between Demo and Live in-app without restarting

How to use:

- Default mode is `demo`. Start the app normally; no API keys needed.
- Toggle via UI: open `/admin/mode` and choose Demo or Live.
- Toggle via API:
  - Get mode: `GET /api/mode`
  - Set mode: `POST /api/mode` with JSON body `{ "mode": "demo" | "live" }`

When switching to Live mode, set these environment variables and restart:

- `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`
- `STRIPE_API_KEY`
- Optionally wire Plaid live via `plaid_mcp.py`.

Files added for Demo Mode:

- `demo_mode.py`: Mode manager, banner helper, toggle routes, Stripe mock
- `xero_demo_data.py`: Sample contacts, invoices, and a P&L dataset
- `plaid_demo_data.py`: Sample accounts and transactions


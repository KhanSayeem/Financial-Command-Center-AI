# Final Debugging Instructions for Assistant Dashboard

## Current Status
- Health page shows `Live data`
- Assistant page loads without server errors
- Revenue and date values update correctly
- Cash position still shows mock data instead of "From Xero integration"

## Debugging Steps
1. Open developer tools (`F12` / `Ctrl+Shift+I`).
2. Visit `https://localhost:8000/assistant/` and refresh.
3. Confirm the console logs `Dashboard data:` and note any errors.
4. If errors appear, capture the message and line number; check elements with IDs `cash-position-value` and `cash-position-trend`.

## Expected Result Once Fixed
- Cash position: `$48,250.75`
- Cash position trend: `From Xero integration` (green text)
- Revenue: `$195,000` (estimated from 13 invoices)
- Last updated: Current date

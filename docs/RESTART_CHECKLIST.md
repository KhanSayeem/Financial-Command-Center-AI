# Application Restart Checklist

1. Stop the running instance (`Ctrl+C`).
2. Restart with `python app_with_setup_wizard.py`.
3. Verify after restart:
   - `https://localhost:8000/health` reports "Live data".
   - `https://localhost:8000/assistant/` shows live Xero figures after refresh.

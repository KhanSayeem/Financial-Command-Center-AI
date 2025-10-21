# Cross-Platform Bootstrap CLI

The FCC bootstrap CLI replaces the Windows-only batch script with a
portable install/launch workflow.

## Installer wrappers

- **Windows**: double-click `bootstrap\bootstrap-install.cmd`. The script
  auto-elevates (UAC prompt) and runs:
  ```
  python -m bootstrap install --no-launch
  ```
  If elevation isn't possible, the CLI prints a fallback command:
  `certutil -user -addstore Root certs\ca.crt`.
- **macOS/Linux**: run `bootstrap/bootstrap-install.sh`. It re-executes
  itself with `sudo` so certificates can be trusted automatically. Without
  sudo, the CLI prints manual trust instructions.

After installation, use `python -m bootstrap launch --detach` (or
`bootstrap\run_windows.cmd launch`, `bootstrap/run_unix.sh launch`).

## Commands

`python -m bootstrap <command>`:

- `install` — create venv, install dependencies (OpenAI/Gemini included),
  verify licence, generate certificates, and trust CA when possible.
- `launch` — start the HTTPS server and open the browser.
- `repair` — re-run setup tasks without deleting data.

## Notes

- The CLI now checks for admin rights on Windows and warns when the trust
  install is skipped.
- When run without elevation, it prints the exact manual command to trust
  the certificate.
- Browsers may cache earlier insecure states; restart the browser or clear
  HSTS after trusting the CA.

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
- **macOS/Linux**: run `bootstrap/bootstrap-install.sh`. It tries to
  elevate with `sudo` so the generated HTTPS certificates can be trusted
  automatically; if `sudo` is unavailable or declined, it continues,
  skips the trust step, and prints manual instructions. The script
  requires Python 3.11+; it detects the interpreter and, when missing,
  prints OS-specific install guidance (or ask users to install Python
  beforehand).
  - macOS bundle: `bootstrap/mac-launch.command` can be double-clicked to
    launch FCC after installation (the first run may require `chmod +x
    bootstrap/mac-launch.command`).
  - Linux bundle: `bootstrap/financial-command-center.desktop` can be
    marked as executable / "Allow Launching" and double-clicked to open
    FCC from the file manager.

After installation, use `python -m bootstrap launch --detach` (or
`bootstrap\run_windows.cmd launch`, `bootstrap/run_unix.sh launch`, or
the new macOS/Linux launch helpers).

## Commands

`python -m bootstrap <command>`:

- `install` - create venv, install dependencies (OpenAI/Gemini included),
  verify licence, generate certificates, and trust CA when possible.
- `launch` - start the HTTPS server and open the browser.
- `repair` - re-run setup tasks without deleting data.

## Notes

- The Windows bootstrapper auto-installs Python 3.11+ if it is missing
  and captures output to `%LOCALAPPDATA%\Financial Command
  Center\bootstrap-<timestamp>.log`.
- The macOS/Linux bootstrapper logs to
  `${XDG_CACHE_HOME:-$HOME/.cache}/financial-command-center/bootstrap-<timestamp>.log`
  (falling back to `/tmp/financial-command-center/`) so users can share
  the transcript when troubleshooting.
- Approving the sudo prompt on macOS/Linux is strongly recommended; if
  the trust step is skipped, import `certs/ca.crt` manually before using
  the HTTPS endpoint to avoid browser warnings.
- When run without elevation, the CLI prints the manual command to trust
  the certificate and points to the log file.
- Browsers may cache earlier insecure states; restart the browser or
  clear HSTS after trusting the CA.

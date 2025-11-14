# FCC Launcher – Plaid Connectivity Troubleshooting

When running the packaged FCC installer (`ultimate_cert_fix.cmd` + launcher build), Plaid calls rely on the host OS for DNS and outbound HTTPS. If Windows silently blocks those requests, you’ll see errors like:

```
urllib3.exceptions.NameResolutionError: Failed to resolve 'sandbox.plaid.com' ([Errno 11001] getaddrinfo failed)
```

## Why it happens

- The launcher ships its own `.venv\Scripts\python.exe`. The first time Windows Defender Firewall sees that binary, it may block outbound traffic until the user approves it.
- The launcher typically runs under `cmd.exe` (because `ultimate_cert_fix.cmd` launches Command Prompt). In some environments the firewall prompt never surfaces, so calls to `sandbox.plaid.com` fail even though the machine can resolve the host elsewhere.

## Quick diagnostic checklist

1. **Verify DNS globally**  
   From any shell: `nslookup sandbox.plaid.com` should return public IPs.
2. **Test TCP/443 in PowerShell**  
   Run **elevated PowerShell** and execute `Test-NetConnection sandbox.plaid.com -Port 443`. If this succeeds, the network itself is fine.
3. **Compare with launcher runtime**  
   If Plaid still fails inside the packaged app, it’s almost always the firewall blocking the launcher’s Python process.

## Recommended fixes

### 1. Run the launcher via PowerShell (first time)

Instead of double-clicking or using Command Prompt:

```powershell
cd C:\path\to\FCC
.\ultimate_cert_fix.cmd
```

Launching from PowerShell (especially as Administrator) forces Windows to show/accept the firewall prompt for `python.exe`, after which Plaid calls succeed.

### 2. Add firewall exceptions manually

Allow outbound connections for:

- `FCC\.venv\Scripts\python.exe`
- `Financial-Command-Center-Launcher.exe` (if you built the EXE)

Windows Defender Firewall → “Allow an app or feature…” → add the paths above.

### 3. Proxy/VPN environments

If the client requires an HTTP(S) proxy, set `HTTPS_PROXY` / `HTTP_PROXY` in the launcher environment (or system-wide) before running `ultimate_cert_fix.cmd`. Plaid’s SDK will respect those variables.

## After the fix

Once Windows has granted outbound access, rerunning `ultimate_cert_fix.cmd` (even from Command Prompt) works consistently—the firewall remembers the decision. Have the client retry the Plaid setup wizard after approving the firewall prompt.

## Support handoff notes

- Ask clients whether they saw a Windows Firewall alert when the launcher first ran. If not, guide them to run via PowerShell or add the explicit rule.
- Collect the output of `nslookup sandbox.plaid.com` and `Test-NetConnection sandbox.plaid.com -Port 443` to confirm network health before escalating further.

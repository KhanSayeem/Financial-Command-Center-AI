#!/usr/bin/env python3
"""Poll an HTTPS endpoint until it responds or a timeout expires."""

from __future__ import annotations

import argparse
import ssl
import sys
import time
import urllib.error
import urllib.request


def wait_for(url: str, attempts: int, delay: float) -> bool:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=5, context=context) as response:
                print(f"Server responded with status {response.status}")
                return True
        except urllib.error.URLError as exc:
            print(f"[{attempt}/{attempts}] Waiting for {url} ... ({exc})")
        except Exception as exc:  # pragma: no cover
            print(f"[{attempt}/{attempts}] Waiting for {url} ... ({exc})")
        time.sleep(delay)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait for HTTPS endpoint to respond")
    parser.add_argument("url", help="Full URL to poll (e.g. https://127.0.0.1:8000/health)")
    parser.add_argument("--attempts", type=int, default=20, help="Number of attempts")
    parser.add_argument("--delay", type=float, default=2.5, help="Delay between attempts (seconds)")
    args = parser.parse_args()

    ok = wait_for(args.url, args.attempts, args.delay)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Simple CLI harness for creating/validating FCC licenses via the local server.
This avoids the GUI prompt so we can verify licenses directly from the console.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import license_manager as lm

# Force console prompts even if tkinter is available.
lm.TK_AVAILABLE = False  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FCC License verification CLI")
    parser.add_argument("--license-key", help="License key to verify (required for non-interactive mode).")
    parser.add_argument("--email", help="Registered email address for the license.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force prompting for a license even if a cached activation exists.",
    )
    return parser.parse_args()


def run_interactive(force_prompt: bool) -> int:
    manager = lm.LicenseManager()
    payload = manager.ensure_valid_license(force_prompt=force_prompt, quiet=False)
    if not payload:
        return 1
    print(json.dumps(payload, indent=2))
    return 0


def run_direct(license_key: str, email: Optional[str]) -> int:
    manager = lm.LicenseManager()
    result = manager._verify_with_server(license_key, email)
    if result.get("ok"):
        print(json.dumps(result["license"], indent=2))
        return 0

    error_code = result.get("error", "unknown")
    print(f"Verification failed: {error_code}", file=sys.stderr)
    return 1


def main() -> int:
    args = parse_args()
    if args.license_key:
        license_key = args.license_key.strip().upper()
        email = (args.email or "").strip() or None
        if not license_key:
            print("License key cannot be blank.", file=sys.stderr)
            return 2
        return run_direct(license_key, email)
    return run_interactive(force_prompt=args.force)


if __name__ == "__main__":
    raise SystemExit(main())

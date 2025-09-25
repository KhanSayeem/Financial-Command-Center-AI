
import json
import os
import subprocess
import sys
from pathlib import Path
import re
import time

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Define paths and commands
HARNESS_OVERRIDE_PATH = Path(__file__).resolve().parent.parent / "secure_config" / "mcp_harness_overrides.json"
XERO_MCP_PATH = Path(__file__).resolve().parent.parent / "xero_mcp.py"
PYTHON_EXE = Path(sys.executable)
JSON_DECODER = json.JSONDecoder()
JSONRPC_OBJECT_START = re.compile(r"{")

def _run_process(command: list[str], env: dict[str, str], requests: list[dict[str, any]]) -> dict[str, any]:
    payload = "\n".join(json.dumps(req) for req in requests) + "\n"
    error: str | None = None
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
    except FileNotFoundError as exc:
        return {
            "json": [],
            "raw": [],
            "stderr": str(exc),
            "returncode": None,
            "error": f"Failed to launch process: {exc}",
        }

    try:
        stdout, stderr = proc.communicate(payload, timeout=90)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        error = f"Timed out after 90 seconds"
    except Exception as exc:
        proc.kill()
        stdout, stderr = proc.communicate()
        error = f"Process error: {exc}"

    raw_lines = stdout.splitlines()
    json_messages = _extract_json_messages(stdout)

    return {
        "json": json_messages,
        "raw": raw_lines,
        "stderr": stderr,
        "returncode": proc.returncode,
        "error": error,
    }

def _extract_json_messages(text: str) -> list[dict[str, any]]:
    messages: list[dict[str, any]] = []
    idx = 0
    length = len(text)
    while idx < length:
        match = JSONRPC_OBJECT_START.search(text, idx)
        if not match:
            break
        start = match.start()
        try:
            obj, offset = JSON_DECODER.raw_decode(text, start)
        except json.JSONDecodeError:
            idx = start + 1
            continue
        if isinstance(obj, dict) and obj.get("jsonrpc") == "2.0":
            messages.append(obj)
            idx = offset
        else:
            idx = start + 1
    return messages

def make_request(req_id: int, method: str, params: dict[str, any]) -> dict[str, any]:
    """Creates a JSON-RPC request."""
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}

def main():
    """Fetches Xero data and updates the harness overrides."""
    print("--- Preparing Xero test data ---")

    # 1. Set up the command and environment for the Xero MCP server
    xero_command = [str(PYTHON_EXE), str(XERO_MCP_PATH)]
    xero_env = os.environ.copy()
    xero_env.update({
        "XERO_CLIENT_ID": "67834CA82C5B49889A95668DAA6EACB0",
        "XERO_CLIENT_SECRET": "yipRhYWEhtCVu7mqgaOYRfFjIYRTWrxRgwOzoGMAFRG2_32F",
    })

    # 2. Generate a unique contact name
    unique_name = f"Test Contact {int(time.time())}"

    # 3. Define the requests to create a contact and an invoice
    requests = [
        make_request(1, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "fcc-tester-prepare", "version": "1.0"},
        }),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        make_request(2, "tools/call", {"name": "xero_create_contact", "arguments": {"name": unique_name}}),
    ]

    # 4. Run the command and get the output
    stage_result = _run_process(xero_command, xero_env, requests)

    # 5. Parse the output to find the contact ID
    messages = stage_result["json"]
    contact_id = None

    for msg in messages:
        if msg.get("id") == 2 and "result" in msg:
            content = msg.get("result", {}).get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text")
                if text:
                    try:
                        response = json.loads(text)
                        contact_id = response.get("contact_id")
                    except json.JSONDecodeError:
                        pass

    if not contact_id:
        print("Could not create a new contact.")
        return

    print(f"Created new contact with ID: {contact_id}")

    # 6. Create a new invoice for the contact
    requests = [
        make_request(1, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "fcc-tester-prepare", "version": "1.0"},
        }),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        make_request(2, "tools/call", {"name": "xero_create_invoice", "arguments": {"contact_id": contact_id, "line_items": [{"description": "Test Item", "quantity": 1, "unit_amount": 100}]}})
    ]

    stage_result = _run_process(xero_command, xero_env, requests)

    # 7. Parse the output to find the invoice ID
    messages = stage_result["json"]
    invoice_id = None

    for msg in messages:
        if msg.get("id") == 2 and "result" in msg:
            content = msg.get("result", {}).get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text")
                if text:
                    try:
                        response = json.loads(text)
                        invoice_id = response.get("invoice_id")
                    except json.JSONDecodeError:
                        pass

    if not invoice_id:
        print("Could not create a new invoice.")
        return

    print(f"Created new invoice with ID: {invoice_id}")

    # 8. Load the harness overrides file
    if HARNESS_OVERRIDE_PATH.exists():
        try:
            overrides = json.loads(HARNESS_OVERRIDE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            overrides = {"global": {}, "tools": {}}
    else:
        overrides = {"global": {}, "tools": {}}

    # 9. Update the overrides with the new IDs
    if "global" not in overrides:
        overrides["global"] = {}
    overrides["global"]["contact_id"] = contact_id
    overrides["global"]["invoice_id"] = invoice_id

    # 10. Save the updated overrides file
    HARNESS_OVERRIDE_PATH.write_text(json.dumps(overrides, indent=2), encoding="utf-8")
    print(f"Successfully updated {HARNESS_OVERRIDE_PATH}")

if __name__ == "__main__":
    main()

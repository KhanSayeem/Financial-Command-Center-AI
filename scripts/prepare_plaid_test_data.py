
import json
import os
import subprocess
import sys
from pathlib import Path
import re

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Define paths and commands
PLAID_MCP_PATH = Path(__file__).resolve().parent.parent / "plaid_mcp.py"
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
    """Creates a new Plaid item and saves the access token."""
    print("--- Preparing Plaid test data ---")

    # 1. Set up the command and environment for the Plaid MCP server
    plaid_command = [str(PYTHON_EXE), str(PLAID_MCP_PATH)]
    plaid_env = os.environ.copy()
    plaid_env.update({
        "PLAID_CLIENT_ID": "68c5a12b8556db00239ce8ce",
        "PLAID_SECRET": "46c49441d3a6b7561f088f36c910d9",
        "PLAID_ENV": "sandbox",
    })

    # 2. Define the requests to create a public token
    requests = [
        make_request(1, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "fcc-tester-prepare", "version": "1.0"},
        }),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        make_request(2, "tools/call", {"name": "sandbox_public_token_create", "arguments": {}}),
    ]

    # 3. Run the command and get the output
    stage_result = _run_process(plaid_command, plaid_env, requests)

    # 4. Parse the output to find the public token
    messages = stage_result["json"]
    public_token = None

    for msg in messages:
        if msg.get("id") == 2 and "result" in msg:
            content = msg.get("result", {}).get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text")
                if text:
                    try:
                        response = json.loads(text)
                        public_token = response.get("public_token")
                    except json.JSONDecodeError:
                        pass

    if not public_token:
        print("Could not find a public token.")
        print("--- Plaid MCP Server Output (Public Token) ---")
        print("STDOUT:")
        for line in stage_result["raw"]:
            print(line)
        print("STDERR:")
        print(stage_result["stderr"])
        print("---------------------------------------------")
        return

    print(f"Found public token: {public_token}")

    # 5. Exchange the public token for an access token
    requests = [
        make_request(1, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "fcc-tester-prepare", "version": "1.0"},
        }),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        make_request(2, "tools/call", {"name": "item_public_token_exchange", "arguments": {"public_token": public_token}}),
    ]

    stage_result = _run_process(plaid_command, plaid_env, requests)

    # 6. Parse the output to find the access token and item ID
    messages = stage_result["json"]
    access_token = None
    item_id = None

    for msg in messages:
        if msg.get("id") == 2 and "result" in msg:
            content = msg.get("result", {}).get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text")
                if text:
                    try:
                        response = json.loads(text)
                        access_token = response.get("access_token")
                        item_id = response.get("item_id")
                    except json.JSONDecodeError:
                        pass

    if not access_token or not item_id:
        print("Could not find an access token or item ID.")
        print("--- Plaid MCP Server Output (Access Token) ---")
        print("STDOUT:")
        for line in stage_result["raw"]:
            print(line)
        print("STDERR:")
        print(stage_result["stderr"])
        print("--------------------------------------------")
        return

    print(f"Found access token: {access_token}")
    print(f"Found item ID: {item_id}")

    # 7. Save the new item to the Plaid store
    plaid_store_path = Path(__file__).resolve().parent.parent / "plaid_store.json"
    store_data = {"items": {"harness-sandbox": {"item_id": item_id, "access_token": access_token}}, "account_mappings": {}}
    plaid_store_path.write_text(json.dumps(store_data, indent=2), encoding="utf-8")

    print("Successfully created and saved new Plaid item 'harness-sandbox'.")
    print("--- Plaid store content after update ---")
    print(plaid_store_path.read_text(encoding="utf-8"))

if __name__ == "__main__":
    main()

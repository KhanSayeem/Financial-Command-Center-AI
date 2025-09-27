
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from setup_wizard import sync_credentials_to_env
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFAULT_CONFIG_PATH = Path("test_claude_config.json")
TIMEOUT_SECONDS = 90

JSONRPC_OBJECT_START = re.compile(r"{")
JSON_DECODER = json.JSONDecoder()

def _create_dynamic_plaid_token() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Generate a fresh Plaid access token using environment credentials."""
    client_id = os.environ.get("PLAID_CLIENT_ID")
    secret = os.environ.get("PLAID_SECRET")

    if not client_id or not secret:
        print("Warning: PLAID_CLIENT_ID and PLAID_SECRET not set in environment")
        return None, None, None

    try:
        import plaid
        from plaid.api import plaid_api
        from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
        from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
        from plaid.model.products import Products
        from plaid.configuration import Configuration
        from plaid.api_client import ApiClient

        configuration = Configuration(
            host="https://sandbox.plaid.com",
            api_key={"clientId": client_id, "secret": secret}
        )
        api_client = ApiClient(configuration)
        client = plaid_api.PlaidApi(api_client)

        public_token_request = SandboxPublicTokenCreateRequest(
            institution_id='ins_109508',
            initial_products=[Products('transactions')]
        )
        public_token_response = client.sandbox_public_token_create(public_token_request)
        public_token = public_token_response['public_token']

        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']

        try:
            from plaid_client_store import store_item
            alias = "harness-sandbox"
            store_item(alias, exchange_response['item_id'], access_token)
            print(f"Generated and stored new Plaid access token: {access_token[:20]}...")
            return alias, access_token, public_token
        except Exception as e:
            print(f"Warning: Could not store token: {e}")
            return "harness-sandbox", access_token, public_token

    except Exception as e:
        print(f"Error creating dynamic Plaid token: {e}")
        return None, None, None

@dataclass
class ToolCallResult:
    name: str
    arguments: Dict[str, Any]
    status: str
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_output: List[str] = field(default_factory=list)

@dataclass
class ServerResult:
    name: str
    file: Path
    command: List[str]
    env: Dict[str, str]
    tools: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[ToolCallResult] = field(default_factory=list)
    list_error: Optional[str] = None
    stderr_lines: List[str] = field(default_factory=list)
    raw_output: List[str] = field(default_factory=list)
    return_code: Optional[int] = None
    stage: str = ""

class MCPTester:
    def __init__(self, config: Dict[str, Any], timeout: int = TIMEOUT_SECONDS) -> None:
        self.config = config
        self.timeout = timeout

    def run(self) -> List[ServerResult]:
        results: List[ServerResult] = []
        for name, entry in self.config.get("mcpServers", {}).items():
            result = self._test_server(name, entry)
            results.append(result)
        return results

    def _test_server(self, name: str, entry: Dict[str, Any]) -> ServerResult:
        command = [entry["command"], *entry.get("args", [])]
        server_path = Path(entry["args"][0]) if entry.get("args") else Path(entry["command"])
        env = os.environ.copy()
        config_env = entry.get("env", {})
        env.update({k: v.strip() if isinstance(v, str) else v for k, v in config_env.items()})

        result = ServerResult(
            name=name,
            file=server_path,
            command=command,
            env={k: env[k] for k in entry.get("env", {})}
        )

        tool_info, stage_result = self._fetch_tools(command, env)
        result.stage = "tools/list"
        if stage_result["stderr"]:
            result.stderr_lines.extend(stage_result["stderr"].splitlines())
        result.raw_output.extend(stage_result["raw"])
        result.return_code = stage_result["returncode"]

        if stage_result.get("error"):
            result.list_error = stage_result["error"]
            return result

        if tool_info is None:
            result.list_error = stage_result["error"] or "Failed to parse tools response"
            return result

        result.tools = tool_info

        calls = self._prepare_calls(tool_info)
        call_stage = self._invoke_tools(command, env, calls)
        result.stage = "tools/call"
        if call_stage["stderr"]:
            result.stderr_lines.extend(call_stage["stderr"].splitlines())
        result.raw_output.extend(call_stage["raw"])
        result.return_code = call_stage["returncode"]
        if call_stage.get("error"):
            result.list_error = call_stage["error"]
        result.tool_results = call_stage["tool_results"]
        return result

    def _fetch_tools(self, command: List[str], env: Dict[str, str]) -> tuple[Optional[List[Dict[str, Any]]], Dict[str, Any]]:
        requests = [
            self._make_request(1, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "fcc-tester", "version": "1.0"},
            }),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            self._make_request(2, "tools/list", {}),
        ]
        stage = self._run_process(command, env, requests)
        tools: Optional[List[Dict[str, Any]]] = None
        for response in stage["json"]:
            if response.get("id") == 2 and "result" in response:
                tools = response["result"].get("tools")
        return tools, stage

    def _prepare_calls(self, tools: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        calls: List[Dict[str, Any]] = []
        next_id = 3
        for tool in tools:
            if tool.get("name") == "item_public_token_exchange":
                schema = tool.get("inputSchema") or {"type": "object", "properties": {}}
                args = self._generate_arguments(schema, tool.get("name", ""), tool.get("description", ""))
                calls.append({
                    "id": next_id,
                    "name": tool["name"],
                    "arguments": args,
                })
                next_id += 1
        return calls

    def _invoke_tools(self, command: List[str], env: Dict[str, str], calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        requests = [
            self._make_request(1, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "fcc-tester", "version": "1.0"},
            }),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        ]
        for call in calls:
            requests.append(self._make_request(call["id"], "tools/call", {
                "name": call["name"],
                "arguments": call["arguments"],
            }))
        stage = self._run_process(command, env, requests)

        tool_results: Dict[int, ToolCallResult] = {
            call["id"]:
            ToolCallResult(name=call["name"], arguments=call["arguments"], status="no-response")
            for call in calls
        }

        for response in stage["json"]:
            resp_id = response.get("id")
            if resp_id not in tool_results:
                continue
            tool_result = tool_results[resp_id]
            if "result" in response:
                tool_result.status = "ok"
                tool_result.response = response["result"]
                ok_flag = None
                if isinstance(tool_result.response, dict):
                    if "ok" in tool_result.response:
                        ok_flag = tool_result.response.get("ok")
                    structured = tool_result.response.get("structuredContent")
                    if isinstance(structured, dict):
                        payload = structured.get("result")
                        if isinstance(payload, dict):
                            if "ok" in payload:
                                ok_flag = payload.get("ok")
                            elif "error" in payload and ok_flag is None:
                                ok_flag = False
                if ok_flag is False:
                    tool_result.status = "reported-error"
                    tool_result.error = json.dumps(tool_result.response)
            elif "error" in response:
                tool_result.status = "rpc-error"
                tool_result.error = json.dumps(response["error"])

        stage["tool_results"] = list(tool_results.values())
        return stage

    def _make_request(self, req_id: int, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}

    def _run_process(self, command: List[str], env: Dict[str, str], requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = "\n".join(json.dumps(req) for req in requests) + "\n"
        error: Optional[str] = None
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
            stdout, stderr = proc.communicate(payload, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            error = f"Timed out after {self.timeout} seconds"
        except Exception as exc:
            proc.kill()
            stdout, stderr = proc.communicate()
            error = f"Process error: {exc}"

        raw_lines = stdout.splitlines()
        json_messages = self._extract_json_messages(stdout)

        return {
            "json": json_messages,
            "raw": raw_lines,
            "stderr": stderr,
            "returncode": proc.returncode,
            "error": error,
        }

    def _extract_json_messages(self, text: str) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
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

    def _generate_arguments(self, schema: Dict[str, Any], tool_name: str, description: str) -> Dict[str, Any]:
        properties = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        arguments: Dict[str, Any] = {}

        _, _, public_token = _create_dynamic_plaid_token()

        for name, prop_schema in properties.items():
            if name == "public_token":
                arguments[name] = public_token
                continue
            if name not in required:
                continue
            arguments[name] = self._sample_value(name, prop_schema)
        return arguments

    def _sample_value(self, name: str, schema: Dict[str, Any]) -> Any:
        schema_type = schema.get("type")
        if isinstance(schema_type, list):
            schema_type = next((t for t in schema_type if t != "null"), schema_type[0])

        if "enum" in schema:
            enum_values = schema["enum"]
            if enum_values:
                return enum_values[0]

        if schema_type == "boolean":
            return schema.get("default", True)

        if schema_type in {"integer", "number"}:
            default = schema.get("default")
            if default is not None:
                return default
            if schema_type == "integer":
                return 1
            return 1.0

        if schema_type == "array":
            item_schema = schema.get("items") or {"type": "string"}
            return [self._sample_value(name, item_schema)]

        if schema_type == "object":
            props = schema.get("properties") or {}
            obj: Dict[str, Any] = {}
            for prop_name, prop_schema in props.items():
                obj[prop_name] = self._sample_value(prop_name, prop_schema)
            return obj

        fmt = schema.get("format", "").lower()
        desc = (schema.get("description") or "").lower()
        if fmt == "date":
            return date.today().isoformat()
        if fmt in {"date-time", "datetime"}:
            return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        if fmt == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        if "email" in name or "email" in desc:
            return "finance@example.com"
        if "currency" in name:
            return "USD"
        if schema.get("default") is not None:
            return schema["default"]
        return f"{name}_sample"

def main() -> int:
    sync_credentials_to_env()
    
    base_dir = Path(__file__).resolve().parent.parent
    venv_python = base_dir / ".venv" / "Scripts" / "python.exe"

    config = {
        "mcpServers": {
            "plaid-banking": {
                "command": str(venv_python),
                "args": [str(base_dir / "plaid_mcp.py")],
                "env": {
                    "PLAID_ENV": "sandbox"
                }
            }
        }
    }
    
    plaid_client = os.environ.get("PLAID_CLIENT_ID")
    plaid_secret = os.environ.get("PLAID_SECRET")
    if plaid_client and plaid_secret:
        plaid_env = {
            "PLAID_CLIENT_ID": plaid_client,
            "PLAID_SECRET": plaid_secret,
        }
        config["mcpServers"]["plaid-banking"]["env"].update(plaid_env)

    tester = MCPTester(config)
    results = tester.run()
    
    for result in results:
        for tool_result in result.tool_results:
            if tool_result.status != "ok":
                print(f"Tool {tool_result.name} failed with status {tool_result.status}")
                if tool_result.error:
                    print(f"Error: {tool_result.error}")
            else:
                print(f"Tool {tool_result.name} passed.")

    return 0

if __name__ == "__main__":
    sys.exit(main())

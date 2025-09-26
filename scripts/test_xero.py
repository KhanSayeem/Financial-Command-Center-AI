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
from datetime import timedelta
from xero_python.accounting import AccountingApi, Contact, Invoices, Invoice, LineItem, Contacts
from xero_python.api_client import ApiClient, Configuration

DEFAULT_CONFIG_PATH = Path("test_claude_config.json")
TIMEOUT_SECONDS = 90

JSONRPC_OBJECT_START = re.compile(r"{ ")
JSON_DECODER = json.JSONDecoder()


def _create_xero_invoice(xero_accounting_api, tenant_id, contact_id) -> str:
    line_items = [
        LineItem(description="Test Item", quantity=1, unit_amount=100, account_code="200")
    ]
    invoice = Invoice(
        type="ACCREC",
        contact=Contact(contact_id=contact_id),
        line_items=line_items,
        date=date.today(),
        due_date=date.today() + timedelta(days=30),
        reference="Test Invoice",
        status="AUTHORISED",
    )
    invoices = Invoices(invoices=[invoice])
    created_invoices = xero_accounting_api.create_invoices(tenant_id, invoices=invoices)
    return created_invoices.invoices[0].invoice_id

def main() -> int:
    sync_credentials_to_env()
    
    base_dir = Path(__file__).resolve().parent.parent
    venv_python = base_dir / ".venv" / "Scripts" / "python.exe"

    config = {
        "mcpServers": {
            "xero-accounting": {
                "command": str(venv_python),
                "args": [str(base_dir / "xero_mcp.py")],
                "env": {}
            }
        }
    }
    
    xero_client_id = os.environ.get("XERO_CLIENT_ID")
    xero_client_secret = os.environ.get("XERO_CLIENT_SECRET")
    if xero_client_id and xero_client_secret:
        xero_env = {
            "XERO_CLIENT_ID": xero_client_id,
            "XERO_CLIENT_SECRET": xero_client_secret,
        }
        config["mcpServers"]["xero-accounting"]["env"].update(xero_env)

    try:
        from xero_client import load_api_client, get_tenant_id, ensure_valid_token
        xero_client = load_api_client()
        ensure_valid_token(xero_client)
        xero_accounting_api = AccountingApi(xero_client)
        tenant_id = get_tenant_id()
        contact = Contact(name=f"Test Contact {int(time.time())}")
        contacts = Contacts(contacts=[contact])
        created_contact = xero_accounting_api.create_contacts(tenant_id, contacts=contacts)
        contact_id = created_contact.contacts[0].contact_id
        invoice_id = _create_xero_invoice(xero_accounting_api, tenant_id, contact_id)
    except Exception as e:
        print(f"Error creating Xero resources: {e}")
        return 1

    tester = MCPTester(config, invoice_id=invoice_id)
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
    def __init__(self, config: Dict[str, Any], timeout: int = TIMEOUT_SECONDS, invoice_id: str = None) -> None:
        self.config = config
        self.timeout = timeout
        self.invoice_id = invoice_id

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
            if tool.get("name") in ["xero_create_contact", "xero_send_invoice_email", "xero_authorise_invoice", "xero_create_payment", "xero_apply_payment_to_invoice"]:
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
            call["id"]: ToolCallResult(name=call["name"], arguments=call["arguments"], status="no-response")
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

        if tool_name == "xero_create_contact":
            arguments["name"] = f"Test Contact {int(time.time())}"
        elif tool_name == "xero_send_invoice_email":
            arguments["invoice_id"] = self.invoice_id
            arguments["email"] = "finance@example.com"
        elif tool_name == "xero_authorise_invoice":
            arguments["invoice_id"] = self.invoice_id
        elif tool_name == "xero_create_payment":
            arguments["invoice_id"] = self.invoice_id
            # Get first available bank account instead of hardcoded ID
            try:
                from xero_client import load_api_client, get_tenant_id, ensure_valid_token
                xero_client = load_api_client()
                ensure_valid_token(xero_client)
                xero_accounting_api = AccountingApi(xero_client)
                tenant_id = get_tenant_id()
                accounts = xero_accounting_api.get_accounts(tenant_id, where="Type==\"BANK\"")
                if accounts.accounts and len(accounts.accounts) > 0:
                    arguments["account_id"] = accounts.accounts[0].account_id
                else:
                    arguments["account_id"] = "562555f2-8cde-4ce9-8203-0363922537a4"  # fallback
            except Exception:
                arguments["account_id"] = "562555f2-8cde-4ce9-8203-0363922537a4"  # fallback
            arguments["amount"] = 1.0
        elif tool_name == "xero_apply_payment_to_invoice":
            arguments["invoice_id"] = self.invoice_id
            arguments["payment_id"] = "655ad293-0b35-4c2c-9a97-0ee979dd365f"
            arguments["date"] = date.today().isoformat()

        for name, prop_schema in properties.items():
            if name not in arguments:
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
            "xero-accounting": {
                "command": str(venv_python),
                "args": [str(base_dir / "xero_mcp.py")],
                "env": {}
            }
        }
    }
    
    xero_client_id = os.environ.get("XERO_CLIENT_ID")
    xero_client_secret = os.environ.get("XERO_CLIENT_SECRET")
    if xero_client_id and xero_client_secret:
        xero_env = {
            "XERO_CLIENT_ID": xero_client_id,
            "XERO_CLIENT_SECRET": xero_client_secret,
        }
        config["mcpServers"]["xero-accounting"]["env"].update(xero_env)

    try:
        from xero_client import load_api_client, get_tenant_id, ensure_valid_token
        xero_client = load_api_client()
        ensure_valid_token(xero_client)
        xero_accounting_api = AccountingApi(xero_client)
        tenant_id = get_tenant_id()
        contact = Contact(name=f"Test Contact {int(time.time())}")
        contacts = Contacts(contacts=[contact])
        created_contact = xero_accounting_api.create_contacts(tenant_id, contacts=contacts)
        contact_id = created_contact.contacts[0].contact_id
        invoice_id = _create_xero_invoice(xero_accounting_api, tenant_id, contact_id)
    except Exception as e:
        print(f"Error creating Xero resources: {e}")
        return 1

    tester = MCPTester(config, invoice_id=invoice_id)
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
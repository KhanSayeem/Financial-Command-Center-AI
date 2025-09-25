from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFAULT_CONFIG_PATH = Path("test_claude_config.json")
TIMEOUT_SECONDS = 90


def _load_plaid_defaults() -> Tuple[Optional[str], Optional[str]]:
    try:
        from plaid_client_store import get_all_items  # type: ignore
    except Exception:
        return None, None
    try:
        items = get_all_items()
    except Exception:
        return None, None
    if not items:
        return None, None
    alias, data = next(iter(items.items()))
    token = None
    if isinstance(data, dict):
        token = data.get("access_token")
    return alias, token


PLAID_ALIAS, PLAID_ACCESS_TOKEN = _load_plaid_defaults()

KNOWN_ARG_OVERRIDES: Dict[str, Any] = {
    "contact_id": "20ed8bc2-691f-4d06-87e7-10914b363142",
    "invoice_id": "fee88eea-f2aa-4a71-a372-33d6d83d3c45",
    "account_id": "562555f2-8cde-4ce9-8203-0363922537a4",
    "payment_id": "655ad293-0b35-4c2c-9a97-0ee979dd365f",
    "tenant_id": "7efae746-d87d-424c-b733-77dbce86462f",
}

HARNESS_OVERRIDE_PATHS = [
    Path("secure_config/mcp_harness_overrides.json"),
    Path("mcp_harness_overrides.json"),
]

TOOL_SPECIFIC_OVERRIDES: Dict[str, Dict[str, Any]] = {}


# Load optional overrides from repo-stored JSON so the harness can use real IDs.
def _load_external_overrides() -> None:
    global KNOWN_ARG_OVERRIDES, TOOL_SPECIFIC_OVERRIDES
    for candidate in HARNESS_OVERRIDE_PATHS:
        if not candidate.exists():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        global_map = data.get("global")
        if isinstance(global_map, dict):
            for key, value in global_map.items():
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                KNOWN_ARG_OVERRIDES[key] = value
        tool_map = data.get("tools")
        if isinstance(tool_map, dict):
            for tool_name, overrides in tool_map.items():
                if not isinstance(overrides, dict):
                    continue
                tool_entry = TOOL_SPECIFIC_OVERRIDES.setdefault(tool_name, {})
                for arg_name, value in overrides.items():
                    if value is None:
                        continue
                    if isinstance(value, str) and not value.strip():
                        continue
                    tool_entry[arg_name] = value


_load_external_overrides()


if PLAID_ACCESS_TOKEN:
    KNOWN_ARG_OVERRIDES.setdefault("access_token", PLAID_ACCESS_TOKEN)
    KNOWN_ARG_OVERRIDES.setdefault("plaid_access_token", PLAID_ACCESS_TOKEN)
if PLAID_ALIAS:
    KNOWN_ARG_OVERRIDES.setdefault("plaid_item_alias", PLAID_ALIAS)
    KNOWN_ARG_OVERRIDES.setdefault("plaid_alias", PLAID_ALIAS)

PLAID_KEY_TOOLS = {
    "accounts_and_balances",
    "transactions_get",
    "auth_get",
    "identity_get",
    "remove_item",
    "sync_bank_transactions_to_xero",
    "categorize_transactions_automatically",
    "auto_categorize_expenses",
    "auto_reconcile_payments",
    "check_balance_alerts",
    "monitor_transactions",
    "scan_plaid_transactions",
    "compliance_generate_tax_report",
    "compliance_detect_suspicious_patterns",
    "generate_cash_flow_forecast",
    "analyze_customer_payment_behavior",
    "detect_revenue_anomalies",
}

JSON_DECODER = json.JSONDecoder()
JSONRPC_OBJECT_START = re.compile(r"{")


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
        env.update({k: v.strip() if isinstance(v, str) else v for k, v in entry.get("env", {}).items()})

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

        for name, prop_schema in properties.items():
            override = self._resolve_override(tool_name, name, prop_schema, description)
            if override is not None:
                arguments[name] = override
                continue
            if name not in required:
                continue
            arguments[name] = self._sample_value(name, prop_schema)

        if not arguments:
            for name, prop_schema in properties.items():
                override = self._resolve_override(tool_name, name, prop_schema, description)
                if override is not None:
                    arguments[name] = override
                elif name in required:
                    arguments[name] = self._sample_value(name, prop_schema)
            if not arguments and properties:
                name, prop_schema = next(iter(properties.items()))
                arguments[name] = self._sample_value(name, prop_schema)

        return arguments

    def _resolve_override(
        self,
        tool_name: str,
        name: str,
        schema: Dict[str, Any],
        description: str,
    ) -> Optional[Any]:
        tool_override = TOOL_SPECIFIC_OVERRIDES.get(tool_name)
        if tool_override and name in tool_override:
            value = tool_override[name]
            if isinstance(value, str) and value.startswith("env:"):
                env_name = value[4:].strip()
                if env_name:
                    return os.environ.get(env_name, "")
                return ""
            return value
        if name in KNOWN_ARG_OVERRIDES and KNOWN_ARG_OVERRIDES[name] is not None:
            return KNOWN_ARG_OVERRIDES[name]
        if name == "key":
            if tool_name in PLAID_KEY_TOOLS:
                if PLAID_ALIAS:
                    return PLAID_ALIAS
                if PLAID_ACCESS_TOKEN:
                    return PLAID_ACCESS_TOKEN
            full_text = " ".join(filter(None, [description, schema.get("description"), tool_name])).lower()
            if "plaid" in full_text or "access token" in full_text:
                if PLAID_ALIAS:
                    return PLAID_ALIAS
                if PLAID_ACCESS_TOKEN:
                    return PLAID_ACCESS_TOKEN
        if name == "access_token" and PLAID_ACCESS_TOKEN:
            return PLAID_ACCESS_TOKEN
        if name == "public_token" and PLAID_ACCESS_TOKEN:
            return PLAID_ACCESS_TOKEN
        return None

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

        # Default to string handling
        fmt = schema.get("format", "").lower()
        desc = (schema.get("description") or "").lower()
        if fmt == "date":
            return date.today().isoformat()
        if fmt in {"date-time", "datetime"}:
            return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        if fmt == "uuid":
            # Return a sentinel that still matches UUID format.
            return "00000000-0000-0000-0000-000000000000"
        if "email" in name or "email" in desc:
            return "finance@example.com"
        if "currency" in name:
            return "USD"
        if "plaid" in desc and PLAID_ALIAS:
            return PLAID_ALIAS
        if schema.get("default") is not None:
            return schema["default"]
        return f"{name}_sample"


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_report(results: List[ServerResult], output_path: Path) -> None:
    data: List[Dict[str, Any]] = []
    for result in results:
        item = asdict(result)
        item["file"] = str(result.file)
        item["command"] = [str(part) for part in result.command]
        data.append(item)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def summarize_results(results: List[ServerResult]) -> None:
    total_servers = len(results)
    total_calls = sum(len(result.tool_results) for result in results)
    successful_calls = sum(1 for result in results for call in result.tool_results if call.status == "ok")
    failed_calls = total_calls - successful_calls

    print(f"Ran {total_servers} server(s); {total_calls} tool calls ({successful_calls} ok, {failed_calls} with issues)")
    for result in results:
        failures = [call for call in result.tool_results if call.status != "ok"]
        if failures:
            print(f"- {result.name}: {len(failures)} issue(s)")
        elif not result.tool_results:
            print(f"- {result.name}: no tool calls executed")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run MCP protocol smoke tests against configured servers.")
    parser.add_argument(
        "config",
        nargs="?",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the Claude MCP configuration JSON (default: test_claude_config.json)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Optional path to write the JSON report (default: mcp_test_report.json)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT_SECONDS,
        help=f"Per-process timeout in seconds (default: {TIMEOUT_SECONDS})",
    )

    args = parser.parse_args(argv)
    config_path = Path(args.config)
    output_path = Path(args.output) if args.output else Path("mcp_test_report.json")

    try:
        config = load_config(config_path)
    except Exception as exc:
        parser.error(str(exc))

    tester = MCPTester(config, timeout=args.timeout)
    results = tester.run()
    write_report(results, output_path)
    summarize_results(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())


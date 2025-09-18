# xero_mcp_warp.py
# Warp-compatible Xero MCP server for Financial Command Center AI
# Based on the original xero_mcp.py but adapted for Warp's MCP compatibility

from __future__ import annotations
import csv, io
import os, shutil, base64, re
import json
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from xero_client import load_api_client, get_tenant_id
from xero_client import set_tenant_id
from xero_python.accounting import Contacts, Contact, Phone, Address
from xero_python.accounting import AccountingApi, Invoices, Invoice, LineItem
from xero_python.accounting import Invoice as _Invoice, Invoices as _Invoices
from xero_python.accounting import Payment, Payments, Allocation

from xero_client import set_tenant_id
from xero_python.exceptions import ApiException

app = FastMCP("xero-mcp-warp")

EXPORTS_DIR = Path(__file__).resolve().parent / "exports_warp"
EXPORTS_DIR.mkdir(exist_ok=True)
TENANT_FILE = Path(__file__).with_name("xero_tenant_warp.json")

def _now_slug():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _api() -> AccountingApi:
    return AccountingApi(load_api_client())

def _tenant() -> str:
    tid = get_tenant_id()
    if not tid:
        raise RuntimeError("No tenant_id found. Log in via Flask app first, then try again.")
    return tid

def _save_tenant(tenant_id: str) -> None:
    try:
        TENANT_FILE.write_text(json.dumps({"tenant_id": tenant_id}, indent=2), encoding="utf-8")
    except Exception:
        pass

def _load_tenant() -> str | None:
    try:
        data = json.loads(TENANT_FILE.read_text(encoding="utf-8"))
        return data.get("tenant_id")
    except Exception:
        return None

def _tenant_or_die(explicit_tenant_id: str | None) -> str:
    """Use an explicitly provided tenant_id, or a stored one, or raise with guidance."""
    tid = explicit_tenant_id or _load_tenant()
    if not tid:
        raise RuntimeError(
            "No tenant_id found. Log in via the Flask app (/login) or call xero_set_tenant first."
        )
    return tid

@app.tool()
def xero_whoami() -> Dict[str, Any]:
    """Show current tenant and simple status."""
    return {
        "server": "xero-mcp-warp",
        "tenant_id": get_tenant_id(), 
        "has_env_client": bool(os.getenv("XERO_CLIENT_ID"))
    }

@app.tool()
def xero_set_tenant(tenant_id: str) -> dict:
    """Manually set the Xero tenant_id stored for MCP."""
    set_tenant_id(tenant_id)
    _save_tenant(tenant_id)
    return {"ok": True, "tenant_id": tenant_id, "saved_to": str(TENANT_FILE)}

@app.tool()
def xero_list_contacts(limit: int = 10, order: str = "Name ASC") -> Dict[str, Any]:
    """List first N contacts."""
    cs = _api().get_contacts(xero_tenant_id=_tenant(), order=order)
    def brief(c):
        return {"name": c.name, "email": c.email_address, "is_customer": bool(c.is_customer), "is_supplier": bool(c.is_supplier)}
    items = [brief(c) for c in (cs.contacts or [])[: max(1, int(limit))]]
    return {"count": len(cs.contacts or []), "first": items}

@app.tool()
def xero_create_contact(
    name: str,
    email: str = "",
    phone: str = "",
    address_line1: str = "",
    city: str = "",
    country: str = ""
) -> dict:
    """
    Create (or upsert) a contact. Xero merges by Name if one exists.
    Works with xero-python v4 by passing lists of Phone/Address directly.
    """
    api = _api(); tid = _tenant()

    phone_list = [Phone(phone_type="DEFAULT", phone_number=phone)] if phone else None
    addr_list = [Address(
        address_type="STREET",
        address_line1=address_line1 or None,
        city=city or None,
        country=country or None
    )] if (address_line1 or city or country) else None

    contact = Contact(
        name=name,
        email_address=email or None,
        phones=phone_list,
        addresses=addr_list,
    )

    created = api.create_contacts(xero_tenant_id=tid, contacts=Contacts(contacts=[contact]))
    c = created.contacts[0]
    return {
        "contact_id": str(c.contact_id),
        "name": c.name,
        "email": c.email_address,
    }


@app.tool()
def xero_get_invoice_pdf(invoice_number: str = "", invoice_id: str = "") -> dict:
    """
    Download an invoice PDF to exports_warp/. Provide either invoice_number or invoice_id.
    Handles bytes/streams/HTTPResponse, base64 strings, and *file-path strings* (temp files).
    """
    api = _api(); tid = _tenant()

    # Resolve invoice_id from number if needed
    inv_id = (invoice_id or "").strip()
    if not inv_id:
        if not invoice_number:
            return {"ok": False, "error": "Provide invoice_number or invoice_id"}
        q = invoice_number.replace('"', '\\"')
        invs = api.get_invoices(xero_tenant_id=tid, where=f'InvoiceNumber=="{q}"')
        if not invs.invoices:
            return {"ok": False, "error": f"No invoice found with number {invoice_number}"}
        inv_id = str(invs.invoices[0].invoice_id)

    # Try whichever PDF method exists
    if hasattr(api, "get_invoice_as_pdf"):
        resp = api.get_invoice_as_pdf(xero_tenant_id=tid, invoice_id=inv_id)
    elif hasattr(api, "get_invoice_pdf"):
        resp = api.get_invoice_pdf(xero_tenant_id=tid, invoice_id=inv_id)
    else:
        return {"ok": False, "error": "SDK missing PDF method (get_invoice_as_pdf / get_invoice_pdf)."}

    # Destination path
    out_path = EXPORTS_DIR / f"invoice_{inv_id}_{_now_slug()}.pdf"

    # Case A) Some builds return a path string to a temp file
    if isinstance(resp, str) and os.path.exists(resp):
        try:
            # If the temp file lacks .pdf, we still copy it with .pdf extension
            shutil.copyfile(resp, out_path)
            size = out_path.stat().st_size
            return {"ok": True, "file": str(out_path), "invoice_id": inv_id, "size": size, "via": "tempfile"}
        finally:
            # Optional: clean up temp file if you want
            # os.remove(resp)
            pass

    # Case B) Stream-like object
    if hasattr(resp, "read"):
        content = resp.read()
        out_path.write_bytes(content)
        return {"ok": True, "file": str(out_path), "invoice_id": inv_id, "size": len(content), "via": "read()"}

    # Case C) urllib3 HTTPResponse-like
    if hasattr(resp, "data"):
        content = resp.data
        out_path.write_bytes(content)
        return {"ok": True, "file": str(out_path), "invoice_id": inv_id, "size": len(content), "via": ".data"}

    # Case D) Direct bytes-ish
    if isinstance(resp, (bytes, bytearray, memoryview)):
        content = bytes(resp)
        out_path.write_bytes(content)
        return {"ok": True, "file": str(out_path), "invoice_id": inv_id, "size": len(content), "via": "bytes"}

    # Case E) String but not a path: handle %PDF or base64
    if isinstance(resp, str):
        s = resp.lstrip()
        if s.startswith("%PDF"):
            content = resp.encode("latin-1", errors="ignore")
            out_path.write_bytes(content)
            return {"ok": True, "file": str(out_path), "invoice_id": inv_id, "size": len(content), "via": "str-%PDF"}
        # try base64
        base64ish = re.fullmatch(r"[A-Za-z0-9+/=\r\n]+", s) and (len(s.strip()) % 4 == 0)
        if base64ish:
            try:
                content = base64.b64decode(s, validate=True)
                out_path.write_bytes(content)
                return {"ok": True, "file": str(out_path), "invoice_id": inv_id, "size": len(content), "via": "base64"}
            except Exception:
                pass
        # If it's a string that isn't a path, %PDF, or base64:
        preview = s[:60].replace("\n", "\\n")
        return {"ok": False, "error": f"Unexpected PDF response string (not a file, %PDF, or base64). Preview: '{preview}'"}

    # Last resort
    try:
        content = bytes(resp)
        out_path.write_bytes(content)
        return {"ok": True, "file": str(out_path), "invoice_id": inv_id, "size": len(content), "via": "bytes(resp)"}
    except Exception:
        return {"ok": False, "error": f"Unhandled PDF response type: {type(resp)}"}


@app.tool()
def xero_org_info() -> dict:
    """
    Show current organisation info: name, base currency, short code, tenant_id.
    """
    api = _api(); tid = _tenant()
    orgs = api.get_organisations(tid)
    if not orgs.organisations:
        return {"ok": False, "error": "No organisations returned"}
    o = orgs.organisations[0]
    return {
        "ok": True,
        "organisation_id": str(o.organisation_id),
        "name": o.name,
        "base_currency": o.base_currency,
        "short_code": o.short_code,
        "tenant_id": tid,
    }

@app.tool()
def xero_find_contact(name: str, limit: int = 5) -> dict:
    """
    Try exact match first; if not found, return up to `limit` fuzzy matches (contains, case-insensitive).
    """
    api = _api(); tid = _tenant()
    q = name.replace('"', '\\"')

    # Exact
    exact = api.get_contacts(xero_tenant_id=tid, where=f'Name=="{q}"')
    if exact.contacts:
        c = exact.contacts[0]
        return {"match": "exact", "contact": {"contact_id": c.contact_id, "name": c.name, "email": c.email_address}}

    # Fuzzy (contains)
    fuzzy = api.get_contacts(xero_tenant_id=tid, where=f'Name.ToLower().Contains("{q.lower()}")', order="Name ASC")
    out = [{"contact_id": c.contact_id, "name": c.name, "email": c.email_address} for c in (fuzzy.contacts or [])[:max(1,int(limit))]]
    return {"match": "fuzzy", "count": len(out), "contacts": out}

@app.tool()
def xero_list_invoices(
    kind: str = "ALL",            # ALL | ACCREC | ACCPAY
    status: str = "",             # e.g., DRAFT, SUBMITTED, AUTHORISED, PAID, VOIDED
    contact_name: str = "",
    date_from: str = "",          # "YYYY-MM-DD"
    date_to: str = "",            # "YYYY-MM-DD"
    limit: int = 10
) -> dict:
    """
    List invoices with optional filters.
    """
    api = _api(); tid = _tenant()
    wh = []

    if kind and kind.upper() in ("ACCREC", "ACCPAY"):
        wh.append(f'Type=="{kind.upper()}"')

    if status:
        wh.append(f'Status=="{status.upper()}"')

    if contact_name:
        q = contact_name.replace('"','\"')
        wh.append(f'Contact.Name.ToLower().Contains("{q.lower()}")')

    # Xero supports Date/DateUTC filters via Date >= DateTime(YYYY,MM,DD)
    def _ymd(s): 
        y,m,d = [int(x) for x in s.split("-")]
        return f"Date >= DateTime({y},{m},{d})"
    def _ymd_to(s): 
        y,m,d = [int(x) for x in s.split("-")]
        return f"Date <= DateTime({y},{m},{d})"

    if date_from:
        wh.append(_ymd(date_from))
    if date_to:
        wh.append(_ymd_to(date_to))

    where = " && ".join(wh) if wh else None
    invs = api.get_invoices(xero_tenant_id=tid, where=where, order="Date DESC")
    def brief(i):
        return {
            "invoice_id": str(i.invoice_id),
            "number": i.invoice_number,
            "type": i.type,
            "status": i.status,
            "contact": getattr(i.contact, "name", None),
            "total": float(i.total or 0),
            "currency": i.currency_code,
            "date": str(i.date) if getattr(i, "date", None) else None
        }
    items = [brief(i) for i in (invs.invoices or [])[:max(1,int(limit))]]
    return {"total": len(invs.invoices or []), "first": items, "where": where}

@app.tool()
def xero_authorise_invoice(
    invoice_id: str = '',
    invoice_number: str = '',
    approval_date: str = '',
    due_date: str = ''
) -> Dict[str, Any]:
    """Authorize a draft invoice so it can be emailed or have payments applied."""
    if not invoice_id and not invoice_number:
        return {"ok": False, "error": "Provide invoice_id or invoice_number"}

    api = _api()
    tid = _tenant()

    def _parse_date(value):
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        value = (value or '').strip()
        if not value:
            raise ValueError
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValueError

    try:
        invoice = None
        if invoice_id:
            fetched = api.get_invoice(xero_tenant_id=tid, invoice_id=invoice_id)
            if hasattr(fetched, 'invoices'):
                invoices = getattr(fetched, "invoices", []) or []
                invoice = invoices[0] if invoices else None
            else:
                invoice = fetched
        else:
            safe_number = invoice_number.replace('"', '\"')
            fetched = api.get_invoices(xero_tenant_id=tid, where=f"InvoiceNumber==\"{safe_number}\"")
            invoices = getattr(fetched, "invoices", []) or []
            invoice = invoices[0] if invoices else None

        if not invoice:
            return {"ok": False, "error": "Invoice not found"}

        current_status = str(getattr(invoice, "status", ""))
        normalized_status = current_status.upper()
        if normalized_status == "AUTHORISED":
            return {
                "ok": True,
                "invoice_id": str(getattr(invoice, "invoice_id", invoice_id)),
                "invoice_number": getattr(invoice, "invoice_number", invoice_number),
                "status": normalized_status,
                "message": "Invoice already authorised"
            }
        if normalized_status not in {"DRAFT", "SUBMITTED"}:
            return {
                "ok": False,
                "error": f"Invoice status must be DRAFT or SUBMITTED to authorise (current: {current_status})"
            }

        payload_kwargs = {"status": "AUTHORISED"}
        try:
            if approval_date:
                payload_kwargs["date"] = _parse_date(approval_date)
        except ValueError:
            return {"ok": False, "error": f"Invalid approval_date format: {approval_date}"}
        try:
            if due_date:
                payload_kwargs["due_date"] = _parse_date(due_date)
        except ValueError:
            return {"ok": False, "error": f"Invalid due_date format: {due_date}"}

        payload = _Invoice(**payload_kwargs)
        target_id = getattr(invoice, "invoice_id", invoice_id)
        try:
            updated = api.update_invoice(tid, target_id, payload)
        except TypeError:
            try:
                updated = api.update_invoice(tid, target_id, _Invoices(invoices=[payload]))
            except TypeError:
                updated = api.update_invoice(
                    xero_tenant_id=tid,
                    invoice_id=target_id,
                    invoices=_Invoices(invoices=[payload])
                )

        updated_invoice = updated.invoices[0] if hasattr(updated, "invoices") else updated

        return {
            "ok": True,
            "invoice_id": str(getattr(updated_invoice, "invoice_id", target_id)),
            "invoice_number": getattr(updated_invoice, "invoice_number", invoice_number or getattr(invoice, "invoice_number", None)),
            "previous_status": current_status,
            "status": str(getattr(updated_invoice, "status", "AUTHORISED"))
        }

    except ApiException as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as e:
        return {"ok": False, "error": f"Failed to authorise invoice: {str(e)}"}


@app.tool()
def xero_create_payment(
    invoice_id: str,
    account_id: str,
    amount: float,
    payment_date: str = "",
    reference: str = "",
    currency_rate: float | None = None,
    is_reconciled: bool | None = None
) -> Dict[str, Any]:
    """Create a payment against an invoice in Xero and return its identifier."""
    invoice_id = (invoice_id or '').strip()
    account_id = (account_id or '').strip()
    if not invoice_id:
        return {"ok": False, "error": "Provide invoice_id"}
    if not account_id:
        return {"ok": False, "error": "Provide account_id for the bank account receiving the payment"}
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        return {"ok": False, "error": "amount must be a number"}
    if amount_value <= 0:
        return {"ok": False, "error": "amount must be greater than zero"}

    api = _api()
    tid = _tenant()

    def _parse_payment_date(value: str):
        value = (value or '').strip()
        if not value:
            return date.today()
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return date.today()

    try:
        parsed_date = _parse_payment_date(payment_date)
        payment_payload = Payment(
            invoice={"invoice_id": invoice_id},
            account={"account_id": account_id},
            amount=amount_value,
            date=parsed_date,
            reference=reference or None,
            currency_rate=currency_rate,
            is_reconciled=is_reconciled
        )
        created = api.create_payments(
            xero_tenant_id=tid,
            payments=Payments(payments=[payment_payload])
        )
        payment = created.payments[0] if getattr(created, "payments", None) else created
        return {
            "ok": True,
            "payment_id": str(getattr(payment, "payment_id", "")),
            "invoice_id": invoice_id,
            "amount": float(getattr(payment, "amount", amount_value) or amount_value),
            "date": str(getattr(payment, "date", parsed_date)),
            "status": getattr(payment, "status", None)
        }
    except ApiException as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as e:
        return {"ok": False, "error": f"Failed to create payment: {str(e)}"}


@app.tool()
def xero_apply_payment_to_invoice(invoice_id: str, payment_id: str) -> Dict[str, Any]:
    """Allocate an existing Xero payment to a specific invoice."""
    invoice_id = (invoice_id or '').strip()
    payment_id = (payment_id or '').strip()
    if not invoice_id or not payment_id:
        return {"ok": False, "error": "Provide both invoice_id and payment_id"}

    api = _api()
    tid = _tenant()

    try:
        payment_response = api.get_payment(xero_tenant_id=tid, payment_id=payment_id)
        if hasattr(payment_response, 'payments'):
            payments_list = payment_response.payments or []
            payment = payments_list[0] if payments_list else None
        else:
            payment = payment_response

        invoice_response = api.get_invoice(xero_tenant_id=tid, invoice_id=invoice_id)
        if hasattr(invoice_response, 'invoices'):
            invoices_list = invoice_response.invoices or []
            invoice = invoices_list[0] if invoices_list else None
        else:
            invoice = invoice_response

        if not payment:
            return {"ok": False, "error": f"Payment {payment_id} not found"}
        if not invoice:
            return {"ok": False, "error": f"Invoice {invoice_id} not found"}

        if float(getattr(invoice, "amount_due", 0) or 0) <= 0:
            return {"ok": False, "error": "Invoice has no outstanding balance"}

        existing_allocations = getattr(payment, "allocations", []) or []
        allocated_total = sum(float(getattr(a, "amount", 0) or 0) for a in existing_allocations)
        available_amount = float(getattr(payment, "amount", 0) or 0) - allocated_total
        if available_amount <= 0:
            return {"ok": False, "error": "Payment has no unallocated balance available"}

        allocation_amount = min(available_amount, float(getattr(invoice, "amount_due", 0) or 0))
        allocation = Allocation(
            invoice={"invoice_id": invoice_id},
            amount=allocation_amount
        )

        updated_payment = Payment(
            payment_id=payment_id,
            allocations=[*existing_allocations, allocation]
        )

        result = api.update_payment(
            xero_tenant_id=tid,
            payment_id=payment_id,
            payments=Payments(payments=[updated_payment])
        )

        return {
            "ok": True,
            "invoice_id": invoice_id,
            "payment_id": payment_id,
            "allocated_amount": allocation_amount,
            "remaining_payment_balance": max(available_amount - allocation_amount, 0),
            "invoice_remaining": float(getattr(invoice, "amount_due", 0) or 0) - allocation_amount,
            "payment_status": getattr(result, "status", None)
        }
    except ApiException as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as e:
        return {"ok": False, "error": f"Failed to apply payment: {str(e)}"}

@app.tool()
def xero_delete_draft_invoice(invoice_number: str) -> dict:
    """
    Mark a DRAFT invoice as DELETED (by invoice number).
    Works across xero-python variants by trying both update styles.
    """
    api = _api(); tid = _tenant()
    q = invoice_number.replace('"', '\\"')
    invs = api.get_invoices(xero_tenant_id=tid, where=f'InvoiceNumber=="{q}"')
    if not invs.invoices:
        return {"ok": False, "error": f"Invoice {invoice_number} not found"}

    inv = invs.invoices[0]
    if str(inv.status).upper() != "DRAFT":
        return {"ok": False, "error": f"Invoice {invoice_number} is not DRAFT (status={inv.status})"}

    # Try style A: single Invoice as positional arg
    try:
        updated = api.update_invoice(tid, inv.invoice_id, _Invoice(status="DELETED"))
        new_status = getattr(updated, "status", None) or (updated.invoices[0].status if getattr(updated, "invoices", None) else None)
        return {"ok": True, "invoice_number": invoice_number, "new_status": str(new_status)}
    except TypeError:
        # Try style B: Invoices wrapper (named or positional)
        try:
            updated = api.update_invoice(tid, inv.invoice_id, _Invoices(invoices=[_Invoice(status="DELETED")]))
            new_status = getattr(updated, "status", None) or (updated.invoices[0].status if getattr(updated, "invoices", None) else None)
            return {"ok": True, "invoice_number": invoice_number, "new_status": str(new_status)}
        except TypeError:
            try:
                updated = api.update_invoice(xero_tenant_id=tid, invoice_id=inv.invoice_id, invoices=_Invoices(invoices=[_Invoice(status="DELETED")]))
                new_status = getattr(updated, "status", None) or (updated.invoices[0].status if getattr(updated, "invoices", None) else None)
                return {"ok": True, "invoice_number": invoice_number, "new_status": str(new_status)}
            except Exception as e:
                return {"ok": False, "error": f"Update failed across variants: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"Update failed: {e}"}

@app.tool()
def xero_export_invoices_csv(limit: int = 100, kind: str = "ALL") -> dict:
    """
    Export up to `limit` invoices to a CSV file in exports_warp/.
    Columns: number, type, status, contact, date, currency, total.
    """
    api = _api(); tid = _tenant()
    where = None
    if kind and kind.upper() in ("ACCREC","ACCPAY"):
        where = f'Type=="{kind.upper()}"'
    invs = api.get_invoices(xero_tenant_id=tid, where=where, order="Date DESC")
    rows = []
    for i in (invs.invoices or [])[:max(1,int(limit))]:
        rows.append([
            i.invoice_number,
            i.type,
            i.status,
            getattr(i.contact, "name", None),
            str(i.date) if getattr(i, "date", None) else "",
            i.currency_code,
            float(i.total or 0),
        ])

    path = EXPORTS_DIR / f"invoices_{kind or 'ALL'}_{_now_slug()}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["number","type","status","contact","date","currency","total"])
        w.writerows(rows)

    return {"ok": True, "count": len(rows), "file": str(path)}



@app.tool()
def xero_dashboard() -> Dict[str, Any]:
    """
    Compact multi-source snapshot: Xero always; Stripe/Plaid included if envs are set.
    """
    out: Dict[str, Any] = {"sources": [], "server": "xero-mcp-warp"}
    # XERO
    try:
        api = _api()
        tid = _tenant()
        accts = api.get_accounts(tid)
        invs  = api.get_invoices(tid, order="Date DESC")
        out["xero"] = {"tenant_id": tid, "accounts_count": len(accts.accounts or []), "invoices_count": len(invs.invoices or []), "last_invoice": (invs.invoices[0].invoice_number if (invs.invoices or []) else None)}
        out["sources"].append("xero")
    except Exception as e:
        out["xero_error"] = str(e)

    # STRIPE (optional)
    try:
        import stripe
        if os.getenv("STRIPE_API_KEY"):
            stripe.api_key = os.getenv("STRIPE_API_KEY")
            charges = stripe.Charge.list(limit=5)
            out["stripe"] = [{"id": c["id"], "amount": c["amount"], "currency": c["currency"], "paid": c["paid"]} for c in charges.get("data", [])]
            out["sources"].append("stripe")
    except Exception as e:
        out["stripe_error"] = str(e)

    # PLAID (optional)
    try:
        import plaid
        from plaid.api import plaid_api
        if os.getenv("PLAID_CLIENT_ID") and os.getenv("PLAID_SECRET") and os.getenv("PLAID_ACCESS_TOKEN"):
            cfg = plaid.Configuration(host=plaid.Environment.Sandbox, api_key={"clientId": os.getenv("PLAID_CLIENT_ID"), "secret": os.getenv("PLAID_SECRET")})
            client = plaid_api.PlaidApi(plaid.ApiClient(cfg))
            from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
            req = AccountsBalanceGetRequest(access_token=os.getenv("PLAID_ACCESS_TOKEN"))
            balances = client.accounts_balance_get(req).to_dict()
            out["plaid"] = balances.get("accounts")
            out["sources"].append("plaid")
    except Exception as e:
        out["plaid_error"] = str(e)

    return out

@app.tool()
def ping() -> Dict[str, Any]:
    """Health check for Warp compatibility"""
    return {
        "ok": True,
        "server": app.name,
        "tenant_id": get_tenant_id(),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    app.run()

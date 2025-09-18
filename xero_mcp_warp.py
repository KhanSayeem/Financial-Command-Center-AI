# xero_mcp_warp.py
# Warp-compatible Xero MCP server for Financial Command Center AI
# Based on the original xero_mcp.py but adapted for Warp's MCP compatibility

from __future__ import annotations
import csv, io
import os, shutil, base64, re
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from xero_client import load_api_client, get_tenant_id
from xero_client import set_tenant_id
from xero_python.accounting import Contacts, Contact, Phone, Address, RequestEmpty
from xero_python.accounting import AccountingApi, Invoices, Invoice, LineItem
from xero_python.accounting import Invoice as _Invoice, Invoices as _Invoices

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

def _extract_api_error(exc: ApiException) -> str:
    """Return a human readable message from a Xero ApiException."""
    message = getattr(exc, 'reason', None) or str(exc)
    body = getattr(exc, 'body', None)
    if body:
        try:
            payload = json.loads(body)
            if isinstance(payload, dict):
                message = payload.get('Message') or payload.get('message') or payload.get('Detail') or message
                elements = payload.get('Elements')
                if not message and isinstance(elements, list) and elements:
                    errors = elements[0].get('ValidationErrors') or []
                    if errors:
                        message = errors[0].get('Message') or message
        except Exception:
            pass
    return message



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
        q = invoice_number.replace('"', '"')
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
def xero_create_invoice(
    contact_id: str,
    line_items: List[Dict],  # [{"description": "...", "quantity": 1, "unit_amount": 100}]
    due_date: Optional[str] = None,
    reference: Optional[str] = None,
    currency_code: Optional[str] = None
) -> Dict:
    """
    Create a new invoice in Xero.

    Args:
        contact_id: The Xero contact ID for the invoice
        line_items: List of line items with description, quantity, and unit_amount
        due_date: Optional due date in YYYY-MM-DD format
        reference: Optional reference/PO number
        currency_code: Optional currency code (defaults to org base currency)

    Returns:
        Dict with invoice details including invoice_id, invoice_number, status
    """
    api = _api()
    tid = _tenant()

    # Build line items
    invoice_line_items = []
    for item in line_items:
        line_item = LineItem(
            description=item.get("description", ""),
            quantity=item.get("quantity", 1),
            unit_amount=item.get("unit_amount", 0)
        )
        invoice_line_items.append(line_item)

    # Create invoice object
    invoice_data = {
        "type": "ACCREC",  # Accounts receivable (sales invoice)
        "contact": {"contact_id": contact_id},
        "line_items": invoice_line_items,
        "status": "DRAFT"
    }

    # Add optional fields
    if due_date:
        from datetime import datetime
        try:
            parsed_date = datetime.strptime(due_date, "%Y-%m-%d").date()
            invoice_data["due_date"] = parsed_date
        except ValueError:
            return {"ok": False, "error": f"Invalid due_date format. Use YYYY-MM-DD, got: {due_date}"}

    if reference:
        invoice_data["reference"] = reference

    if currency_code:
        invoice_data["currency_code"] = currency_code

    # Create the invoice
    invoice = Invoice(**invoice_data)
    invoices = Invoices(invoices=[invoice])

    try:
        result = api.create_invoices(xero_tenant_id=tid, invoices=invoices)
        created_invoice = result.invoices[0]

        return {
            "ok": True,
            "invoice_id": str(created_invoice.invoice_id),
            "invoice_number": created_invoice.invoice_number,
            "status": created_invoice.status,
            "type": created_invoice.type,
            "total": float(created_invoice.total or 0),
            "currency_code": created_invoice.currency_code,
            "contact_name": getattr(created_invoice.contact, "name", None),
            "due_date": str(created_invoice.due_date) if getattr(created_invoice, "due_date", None) else None,
            "reference": created_invoice.reference
        }
    except Exception as e:
        return {"ok": False, "error": f"Failed to create invoice: {str(e)}"}


@app.tool()
def xero_duplicate_invoice(invoice_id: str) -> Dict[str, Any]:
    """Copy an existing invoice to create a new draft invoice."""
    api = _api()
    tid = _tenant()

    try:
        original = api.get_invoice(xero_tenant_id=tid, invoice_id=invoice_id)
        if hasattr(original, 'invoices'):
            invoices = original.invoices or []
            if not invoices:
                return {"ok": False, "error": f"Invoice {invoice_id} not found"}
            orig_invoice = invoices[0]
        else:
            orig_invoice = original

        contact = getattr(orig_invoice, 'contact', None)
        contact_id = getattr(contact, 'contact_id', None)
        if not contact_id:
            return {"ok": False, "error": "Original invoice is missing a contact reference."}

        line_items: List[LineItem] = []
        for item in (getattr(orig_invoice, 'line_items', []) or []):
            line_item_data: Dict[str, Any] = {
                'description': getattr(item, 'description', ''),
                'quantity': getattr(item, 'quantity', 1),
                'unit_amount': getattr(item, 'unit_amount', 0),
            }
            account_code = getattr(item, 'account_code', None)
            tax_type = getattr(item, 'tax_type', None)
            item_code = getattr(item, 'item_code', None)
            if account_code:
                line_item_data['account_code'] = account_code
            if tax_type:
                line_item_data['tax_type'] = tax_type
            if item_code:
                line_item_data['item_code'] = item_code
            line_items.append(LineItem(**line_item_data))

        if not line_items:
            return {"ok": False, "error": "Original invoice has no line items to duplicate."}

        invoice_kwargs: Dict[str, Any] = {
            'type': getattr(orig_invoice, 'type', 'ACCREC'),
            'contact': Contact(contact_id=str(contact_id)),
            'line_items': line_items,
            'status': 'DRAFT',
        }

        currency_code = getattr(orig_invoice, 'currency_code', None)
        if currency_code:
            invoice_kwargs['currency_code'] = currency_code
        due_date = getattr(orig_invoice, 'due_date', None)
        if due_date:
            invoice_kwargs['due_date'] = due_date
        reference = getattr(orig_invoice, 'reference', None)
        if reference:
            invoice_kwargs['reference'] = f"Copy of {reference}"
        line_amount_types = getattr(orig_invoice, 'line_amount_types', None)
        if line_amount_types:
            invoice_kwargs['line_amount_types'] = line_amount_types

        new_invoice = Invoice(**invoice_kwargs)
        response = api.create_invoices(xero_tenant_id=tid, invoices=Invoices(invoices=[new_invoice]))
        created = response.invoices[0]

        return {
            'ok': True,
            'original_invoice_id': invoice_id,
            'new_invoice_id': str(created.invoice_id),
            'new_invoice_number': created.invoice_number,
            'status': created.status,
            'total': float(created.total or 0),
        }
    except ApiException as exc:
        message = _extract_api_error(exc)
        return {"ok": False, "error": f"Failed to duplicate invoice: {message}", "details": {"status_code": getattr(exc, 'status', None)}}
    except Exception as e:
        return {"ok": False, "error": f"Failed to duplicate invoice: {str(e)}"}

@app.tool()
def xero_send_invoice_email(invoice_id: str, email: str) -> Dict[str, Any]:
    """Email an invoice to a client, ensuring Xero receives the required request payload."""
    email = (email or '').strip()
    if not email:
        return {"ok": False, "error": "Provide the destination email address."}

    api = _api()
    tid = _tenant()

    contact_email_updated = False
    previous_email = None

    try:
        invoice_response = api.get_invoice(xero_tenant_id=tid, invoice_id=invoice_id)
        if hasattr(invoice_response, 'invoices'):
            invoices = invoice_response.invoices or []
            if not invoices:
                return {"ok": False, "error": f"Invoice {invoice_id} not found"}
            invoice = invoices[0]
        else:
            invoice = invoice_response

        contact = getattr(invoice, 'contact', None)
        contact_id = getattr(contact, 'contact_id', None)
        if not contact_id:
            return {"ok": False, "error": "Invoice does not have an associated contact."}

        current_email = getattr(contact, 'email_address', '') or ''
        previous_email = current_email
        if email.lower() != current_email.lower():
            update_payload = Contacts(contacts=[Contact(contact_id=str(contact_id), email_address=email)])
            api.update_contact(xero_tenant_id=tid, contact_id=str(contact_id), contacts=update_payload)
            contact_email_updated = True

        if hasattr(api, 'email_invoice'):
            api.email_invoice(xero_tenant_id=tid, invoice_id=invoice_id, request_empty=RequestEmpty())
            method = 'api_email'
        else:
            updated_invoice = Invoice(status="SUBMITTED")
            api.update_invoice(xero_tenant_id=tid, invoice_id=invoice_id, invoices=Invoices(invoices=[updated_invoice]))
            method = 'status_update'

        response = {
            'ok': True,
            'invoice_id': invoice_id,
            'email': email,
            'method': method,
            'message': 'Invoice emailed successfully' if method == 'api_email' else 'Invoice status updated. Email manually from Xero.',
        }
        if contact_email_updated:
            response['contact_email_updated'] = True
            response['previous_email'] = previous_email
        return response

    except ApiException as exc:
        message = _extract_api_error(exc)
        if contact_email_updated and previous_email is not None and previous_email.lower() != email.lower():
            try:
                revert_payload = Contacts(contacts=[Contact(contact_id=str(contact_id), email_address=previous_email or None)])
                api.update_contact(xero_tenant_id=tid, contact_id=str(contact_id), contacts=revert_payload)
            except Exception:
                pass
        return {"ok": False, "error": f"Failed to email invoice: {message}", "details": {"status_code": getattr(exc, 'status', None)}}
    except Exception as e:
        return {"ok": False, "error": f"Failed to email invoice: {str(e)}"}

@app.tool()
def xero_apply_payment_to_invoice(invoice_id: str, payment_id: str) -> Dict[str, Any]:
    """
    Link a payment to an invoice in Xero.

    Args:
        invoice_id: The ID of the invoice to apply payment to
        payment_id: The ID of the payment to apply

    Returns:
        Dict with success status or error
    """
    api = _api()
    tid = _tenant()

    try:
        from xero_python.accounting import Payment, Payments, Allocation, Allocations

        # Get the payment and invoice details
        payment = api.get_payment(xero_tenant_id=tid, payment_id=payment_id)
        invoice = api.get_invoice(xero_tenant_id=tid, invoice_id=invoice_id)

        if not payment:
            return {"ok": False, "error": f"Payment {payment_id} not found"}
        if not invoice:
            return {"ok": False, "error": f"Invoice {invoice_id} not found"}

        # Create allocation linking payment to invoice
        allocation = Allocation(
            invoice={"invoice_id": invoice_id},
            amount=min(float(payment.amount or 0), float(invoice.amount_due or 0))
        )

        # Update the payment with the allocation
        updated_payment = Payment(
            payment_id=payment_id,
            allocations=[allocation]
        )

        payments = Payments(payments=[updated_payment])
        result = api.update_payment(xero_tenant_id=tid, payment_id=payment_id, payments=payments)

        return {
            "ok": True,
            "invoice_id": invoice_id,
            "payment_id": payment_id,
            "allocated_amount": allocation.amount,
            "message": "Payment successfully applied to invoice"
        }

    except Exception as e:
        return {"ok": False, "error": f"Failed to apply payment to invoice: {str(e)}"}

@app.tool()
def xero_get_profit_loss(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Get profit and loss statement for a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Dict with P&L data or error
    """
    api = _api()
    tid = _tenant()

    try:
        from datetime import datetime
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Xero API call for P&L report
        report = api.get_report_profit_and_loss(
            xero_tenant_id=tid,
            from_date=start,
            to_date=end
        )

        return {
            "ok": True,
            "report_id": getattr(report, "report_id", None),
            "report_name": getattr(report, "report_name", "Profit and Loss"),
            "report_date": f"{start_date} to {end_date}",
            "report_data": getattr(report, "reports", None)
        }

    except ValueError:
        return {"ok": False, "error": "Invalid date format. Use YYYY-MM-DD"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to get P&L report: {str(e)}"}

@app.tool()
def xero_get_balance_sheet(date: str) -> Dict[str, Any]:
    """
    Get balance sheet for a specific date.

    Args:
        date: Date in YYYY-MM-DD format

    Returns:
        Dict with balance sheet data or error
    """
    api = _api()
    tid = _tenant()

    try:
        from datetime import datetime
        report_date = datetime.strptime(date, "%Y-%m-%d").date()

        # Xero API call for balance sheet
        report = api.get_report_balance_sheet(
            xero_tenant_id=tid,
            date=report_date
        )

        return {
            "ok": True,
            "report_id": getattr(report, "report_id", None),
            "report_name": getattr(report, "report_name", "Balance Sheet"),
            "report_date": date,
            "report_data": getattr(report, "reports", None)
        }

    except ValueError:
        return {"ok": False, "error": "Invalid date format. Use YYYY-MM-DD"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to get balance sheet: {str(e)}"}

@app.tool()
def xero_get_aged_receivables() -> Dict[str, Any]:
    """
    Get aged receivables report showing outstanding invoices by age.

    Returns:
        Dict with aged receivables data or error
    """
    api = _api()
    tid = _tenant()

    try:
        # Xero API call for aged receivables
        report = api.get_report_aged_receivables_by_contact(
            xero_tenant_id=tid
        )

        return {
            "ok": True,
            "report_id": getattr(report, "report_id", None),
            "report_name": getattr(report, "report_name", "Aged Receivables"),
            "report_data": getattr(report, "reports", None)
        }

    except Exception as e:
        return {"ok": False, "error": f"Failed to get aged receivables: {str(e)}"}

@app.tool()
def xero_get_cash_flow_statement(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """Get cash flow insights using Xero's bank summary report."""
    api = _api()
    tid = _tenant()

    from datetime import datetime

    report_args: Dict[str, Any] = {}
    if start_date or end_date:
        if not (start_date and end_date):
            return {"ok": False, "error": "Provide both start_date and end_date when requesting a cash flow range."}
        try:
            report_args['from_date'] = datetime.strptime(start_date, "%Y-%m-%d").date()
            report_args['to_date'] = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return {"ok": False, "error": "Invalid date format. Use YYYY-MM-DD."}

    try:
        report = api.get_report_bank_summary(xero_tenant_id=tid, **report_args)

        return {
            'ok': True,
            'report_id': getattr(report, 'report_id', None),
            'report_name': 'Cash Flow (Bank Summary)',
            'report_parameters': report_args,
            'report_data': getattr(report, 'reports', None),
        }
    except ApiException as exc:
        message = _extract_api_error(exc)
        return {"ok": False, "error": f"Failed to get cash flow statement: {message}", "details": {"status_code": getattr(exc, 'status', None)}}
    except Exception as e:
        return {"ok": False, "error": f"Failed to get cash flow statement: {str(e)}"}

@app.tool()
def xero_bulk_create_invoices(invoice_list: List[Dict]) -> Dict[str, Any]:
    """
    Create multiple invoices in batch.

    Args:
        invoice_list: List of invoice dictionaries with contact_id, line_items, etc.

    Returns:
        Dict with creation results or errors
    """
    api = _api()
    tid = _tenant()

    try:
        invoices_to_create = []

        for invoice_data in invoice_list:
            # Build line items
            invoice_line_items = []
            for item in invoice_data.get("line_items", []):
                line_item = LineItem(
                    description=item.get("description", ""),
                    quantity=item.get("quantity", 1),
                    unit_amount=item.get("unit_amount", 0)
                )
                invoice_line_items.append(line_item)

            # Create invoice object - Fix: Properly create Contact object
            contact = Contact(contact_id=invoice_data["contact_id"])
            invoice = Invoice(
                type="ACCREC",
                contact=contact,
                line_items=invoice_line_items,
                status="DRAFT",
                currency_code=invoice_data.get("currency_code"),
                reference=invoice_data.get("reference")
            )

            if invoice_data.get("due_date"):
                from datetime import datetime
                try:
                    parsed_date = datetime.strptime(invoice_data["due_date"], "%Y-%m-%d").date()
                    invoice.due_date = parsed_date
                except ValueError:
                    pass

            invoices_to_create.append(invoice)

        # Batch create
        invoices = Invoices(invoices=invoices_to_create)
        result = api.create_invoices(xero_tenant_id=tid, invoices=invoices)

        created_invoices = []
        for inv in result.invoices:
            created_invoices.append({
                "invoice_id": str(inv.invoice_id),
                "invoice_number": inv.invoice_number,
                "status": inv.status,
                "total": float(inv.total or 0)
            })

        return {
            "ok": True,
            "created_count": len(created_invoices),
            "invoices": created_invoices
        }

    except Exception as e:
        return {"ok": False, "error": f"Failed to bulk create invoices: {str(e)}"}

@app.tool()
def xero_export_chart_of_accounts() -> Dict[str, Any]:
    """
    Export chart of accounts structure to CSV.

    Returns:
        Dict with export file path or error
    """
    api = _api()
    tid = _tenant()

    try:
        accounts = api.get_accounts(xero_tenant_id=tid)

        rows = []
        for account in accounts.accounts or []:
            rows.append([
                account.code,
                account.name,
                account.type,
                account.description or "",
                account.tax_type or "",
                getattr(account, "enable_payments_to_account", False),
                account.status
            ])

        path = EXPORTS_DIR / f"chart_of_accounts_{_now_slug()}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "code", "name", "type", "description",
                "tax_type", "enable_payments", "status"
            ])
            writer.writerows(rows)

        return {
            "ok": True,
            "count": len(rows),
            "file": str(path)
        }

    except Exception as e:
        return {"ok": False, "error": f"Failed to export chart of accounts: {str(e)}"}

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

# -----------------------------------------------------------------------------
# Cross-Platform Integration: Stripe and Xero Integration
# -----------------------------------------------------------------------------

@app.tool()
def xero_process_stripe_payment_data(
    stripe_payment_data: List[Dict[str, Any]],
    default_contact_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process Stripe payment data to create Xero invoices.

    Args:
        stripe_payment_data: List of Stripe payment data from sync_stripe_payments_to_xero
        default_contact_id: Default Xero contact ID if customer mapping is not available

    Returns:
        Dict with invoice creation results
    """
    api = _api()
    tid = _tenant()

    created_invoices = []
    errors = []

    try:
        for payment in stripe_payment_data:
            try:
                # Create line item for the payment
                line_items = [{
                    "description": payment.get("description", f"Stripe Payment {payment.get('stripe_charge_id')}"),
                    "quantity": 1,
                    "unit_amount": payment.get("amount_dollars", 0)
                }]

                # Use provided contact or default
                contact_id = payment.get("xero_contact_id") or default_contact_id
                if not contact_id:
                    errors.append({
                        "stripe_charge_id": payment.get("stripe_charge_id"),
                        "error": "No Xero contact ID available"
                    })
                    continue

                # Create the invoice
                result = xero_create_invoice(
                    contact_id=contact_id,
                    line_items=line_items,
                    reference=f"Stripe-{payment.get('stripe_charge_id')}",
                    currency_code=payment.get("currency", "USD").upper()
                )

                if result.get("ok"):
                    created_invoices.append({
                        "stripe_charge_id": payment.get("stripe_charge_id"),
                        "xero_invoice_id": result.get("invoice_id"),
                        "xero_invoice_number": result.get("invoice_number"),
                        "amount": payment.get("amount_dollars")
                    })
                else:
                    errors.append({
                        "stripe_charge_id": payment.get("stripe_charge_id"),
                        "error": result.get("error")
                    })

            except Exception as e:
                errors.append({
                    "stripe_charge_id": payment.get("stripe_charge_id"),
                    "error": str(e)
                })

        return {
            "ok": True,
            "server": "xero-mcp-warp",
            "processed_payments": len(stripe_payment_data),
            "invoices_created": len(created_invoices),
            "errors_count": len(errors),
            "created_invoices": created_invoices,
            "errors": errors
        }

    except Exception as e:
        return {"ok": False, "error": f"Failed to process Stripe payments: {str(e)}", "server": "xero-mcp-warp"}


@app.tool()
def xero_import_bank_feed(
    bank_feed_data: List[Dict[str, Any]],
    xero_bank_account_id: str
) -> Dict[str, Any]:
    """
    Import bank transaction feed data from Plaid into Xero.

    Args:
        bank_feed_data: Bank transaction data from sync_bank_transactions_to_xero
        xero_bank_account_id: Xero bank account ID to import transactions to

    Returns:
        Dict with import results
    """
    api = _api()
    tid = _tenant()

    try:
        from xero_python.accounting import BankTransaction, BankTransactions, LineItem as BankLineItem

        created_transactions = []
        errors = []

        for tx_data in bank_feed_data:
            try:
                # Create bank transaction line item
                line_item = BankLineItem(
                    description=tx_data.get("description", "Bank Transaction"),
                    unit_amount=tx_data.get("amount", 0),
                    quantity=1
                )

                # Create bank transaction
                bank_transaction = BankTransaction(
                    type="SPEND" if tx_data.get("type") == "DEBIT" else "RECEIVE",
                    contact=None,  # Will need contact mapping for proper categorization
                    line_items=[line_item],
                    bank_account={"account_id": xero_bank_account_id},
                    date=datetime.strptime(tx_data.get("date"), "%Y-%m-%d").date() if tx_data.get("date") else datetime.now().date(),
                    reference=tx_data.get("plaid_transaction_id", "")
                )

                bank_transactions = BankTransactions(bank_transactions=[bank_transaction])
                result = api.create_bank_transactions(xero_tenant_id=tid, bank_transactions=bank_transactions)

                if result.bank_transactions:
                    created_tx = result.bank_transactions[0]
                    created_transactions.append({
                        "plaid_transaction_id": tx_data.get("plaid_transaction_id"),
                        "xero_transaction_id": str(created_tx.bank_transaction_id),
                        "amount": tx_data.get("amount"),
                        "description": tx_data.get("description")
                    })

            except Exception as e:
                errors.append({
                    "plaid_transaction_id": tx_data.get("plaid_transaction_id"),
                    "error": str(e)
                })

        return {
            "ok": True,
            "server": "xero-mcp-warp",
            "processed_transactions": len(bank_feed_data),
            "imported_count": len(created_transactions),
            "errors_count": len(errors),
            "imported_transactions": created_transactions,
            "errors": errors,
            "xero_bank_account_id": xero_bank_account_id
        }

    except Exception as e:
        return {"ok": False, "error": f"Failed to import bank feed: {str(e)}", "server": "xero-mcp-warp"}


@app.tool()
def xero_auto_categorize_transactions(
    categorized_transaction_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Auto-categorize imported transactions using AI categorization data from Plaid.

    Args:
        categorized_transaction_data: Categorized transaction data from categorize_transactions_automatically

    Returns:
        Dict with categorization results and account mapping suggestions
    """
    api = _api()
    tid = _tenant()

    try:
        # Get chart of accounts for mapping
        accounts = api.get_accounts(xero_tenant_id=tid)
        account_mapping = {}

        # Create a mapping of accounting categories to Xero accounts
        for account in accounts.accounts or []:
            # Fix: Handle None values and properly access account attributes
            account_name = getattr(account, "name", "") or ""
            account_name_lower = account_name.lower()
            
            # Fix: Safely access account type
            account_type = getattr(account, "type", "") or ""
            if account_type:
                account_type = account_type.lower()
            else:
                account_type = ""

            account_code = getattr(account, "code", "") or ""
            
            # Map common accounting categories to Xero accounts
            if "office" in account_name_lower or "supplies" in account_name_lower:
                account_mapping["office_expenses"] = account_code
            elif "travel" in account_name_lower or "transport" in account_name_lower:
                account_mapping["travel"] = account_code
            elif "meal" in account_name_lower or "entertainment" in account_name_lower:
                account_mapping["meals"] = account_code
            elif "utility" in account_name_lower or "utilities" in account_name_lower:
                account_mapping["utilities"] = account_code
            elif "professional" in account_name_lower or "legal" in account_name_lower:
                account_mapping["professional_services"] = account_code
            elif "marketing" in account_name_lower or "advertising" in account_name_lower:
                account_mapping["marketing"] = account_code
            elif "equipment" in account_name_lower or "computer" in account_name_lower:
                account_mapping["equipment"] = account_code
            elif "rent" in account_name_lower:
                account_mapping["rent"] = account_code
            elif "insurance" in account_name_lower:
                account_mapping["insurance"] = account_code
            elif "bank" in account_name_lower and "fee" in account_name_lower:
                account_mapping["bank_fees"] = account_code
            elif account_type == "revenue" or "income" in account_name_lower:
                account_mapping["revenue"] = account_code

        # Process categorized transactions
        mapped_transactions = []
        unmapped_transactions = []

        for tx in categorized_transaction_data:
            accounting_category = tx.get("accounting_category")
            xero_account_code = account_mapping.get(accounting_category)

            mapped_tx = {
                "plaid_transaction_id": tx.get("transaction_id"),
                "description": tx.get("description"),
                "amount": tx.get("amount"),
                "accounting_category": accounting_category,
                "confidence": tx.get("confidence"),
                "xero_account_code": xero_account_code,
                "ready_for_coding": xero_account_code is not None and tx.get("confidence", 0) > 0.7
            }

            if xero_account_code:
                mapped_transactions.append(mapped_tx)
            else:
                unmapped_transactions.append(mapped_tx)

        return {
            "ok": True,
            "server": "xero-mcp-warp",
            "total_transactions": len(categorized_transaction_data),
            "mapped_count": len(mapped_transactions),
            "unmapped_count": len(unmapped_transactions),
            "account_mapping": account_mapping,
            "mapped_transactions": mapped_transactions,
            "unmapped_transactions": unmapped_transactions,
            "high_confidence_ready": len([tx for tx in mapped_transactions if tx.get("ready_for_coding")])
        }

    except Exception as e:
        return {"ok": False, "error": f"Failed to auto-categorize transactions: {str(e)}", "server": "xero-mcp-warp"}


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
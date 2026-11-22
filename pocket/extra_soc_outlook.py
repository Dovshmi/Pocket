"""Pocket Extra: compose an unsent SOC request from one selected Excel row.

No mail is sent, no recipient is pre-selected, no workbook/database is changed,
and no contact details or ticket descriptions are saved in Pocket.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
import os
import re
import sys
import unicodedata
from urllib.parse import quote

PLACEHOLDER = "[להשלמה]"
SOC_SUBJECT_SUFFIX = "פנייה לSOC"
_COLUMN_SUFFIX = re.compile(r"\s*\([A-Z]{1,3}\)\s*$", re.IGNORECASE)
_NONWORD = re.compile(r"[^\w\u0590-\u05FF]+", re.UNICODE)
_FG_PREFIX = re.compile(r"^\s*FG[\s_-]*(\d{1,3})(?:\.(\d{1,3}))?(?!\d)", re.IGNORECASE)
_BODY_TAG = re.compile(r"<body\b[^>]*>", flags=re.IGNORECASE)


@dataclass(frozen=True)
class SocDetails:
    customer: str
    line_code: str
    fortigate_ip: str
    vdom: str
    worksheet: str

    def missing(self):
        return tuple(caption for caption, value in (
            ("שם לקוח", self.customer),
            ("קוד קו", self.line_code),
            ("IP FortiGate", self.fortigate_ip),
            ("VDOM", self.vdom),
        ) if not value)


@dataclass(frozen=True)
class SocDraft:
    subject: str
    body: str
    html_fragment: str
    details: SocDetails


def _clean(raw, *, max_length=200):
    # Flatten cells to one line; HTML is escaped separately. Drop control chars
    # to avoid fake mail header lines or unexpectedly large subject/body values.
    normalized = unicodedata.normalize("NFKC", str(raw or ""))
    normalized = "".join(c for c in normalized
                         if c.isprintable() and c not in "\r\n\t")
    return " ".join(normalized.split())[:max_length].strip()


def _header(raw):
    label = _COLUMN_SUFFIX.sub("", _clean(raw, max_length=120))
    label = unicodedata.normalize("NFKC", label).casefold()
    return " ".join(_NONWORD.sub(" ", label).split())


def _get_field(fields, preferred, *, reject=()):
    """Find a value using the actual Excel header, never an arbitrary match.

    Critical: 'קוד קבוצה' is NOT a customer circuit/line code.
    """
    entries = [(_header(name), _clean(value), str(name))
               for name, value in fields if _clean(value)]
    for expected in preferred:
        for header, value, _raw in entries:
            if header == expected and not any(word in header for word in reject):
                return value
    return ""


def fortigate_ip_from_sheet(sheet_name):
    """FG25 -> 10.238.2.25; FG-2.8-METRO1 -> 10.238.2.8.

    'FG Projects', unknown sheet naming or an invalid host octet is not a
    safe source of a FortiGate IP: leave blank for manual completion.
    """
    name = _clean(sheet_name, max_length=180)
    match = _FG_PREFIX.match(name)
    if not match:
        return ""
    # In names like FG-2.8, the last numeric component is the device number.
    device = int(match.group(2) or match.group(1))
    return f"10.238.2.{device}" if 1 <= device <= 254 else ""


def details_from_hit(hit):
    """Extract only the four approved fields from Local or Database ExcelHit."""
    fields = tuple(hit.fields)
    customer = _get_field(fields, (
        "לקוח", "שם לקוח", "שם הלקוח", "שם העסק", "שם עסק",
        "שם חברה", "חברה", "customer", "customer name", "client",
        "business", "business name",
    ))
    line_code = _get_field(fields, (
        "קוד קו", "מספר קו", "מס קו", "מס קו ", "קוד קישור",
        "מספר קישור", "מס קישור", "מספר קו לקוח", "line code",
        "line number", "circuit id", "circuit code",
    ), reject=("קבוצה", "group"))
    vdom = _get_field(fields, (
        "vdom", "שם vdom", "vdom name", "vdom id", "vdom לקוח",
        "vdom customer",
    ))
    return SocDetails(
        customer=customer, line_code=line_code,
        fortigate_ip=fortigate_ip_from_sheet(hit.sheet),
        vdom=vdom, worksheet=_clean(hit.sheet),
    )


def make_soc_draft(hit):
    info = details_from_hit(hit)
    customer = info.customer or PLACEHOLDER
    line = info.line_code or PLACEHOLDER
    subject = f"{customer} {line} {SOC_SUBJECT_SUFFIX}"
    values = (
        ("שם העסק / הלקוח", customer),
        ("קוד קו", line),
        ("כתובת FortiGate", info.fortigate_ip or PLACEHOLDER),
        ("VDOM", info.vdom or PLACEHOLDER),
        ("איש קשר", PLACEHOLDER),
        ("מספר טלפון", PLACEHOLDER),
        ("תיאור התקלה / הבקשה", PLACEHOLDER),
        ("מספר פנייה קודמת (אם קיימת)", PLACEHOLDER),
        ("באישור מומחה – שם המומחה", PLACEHOLDER),
    )
    plain_lines = ["שלום,", "", "אבקש את טיפול צוות SOC עבור הלקוח הבא:", ""]
    plain_lines.extend(f"{name}: {value}" for name, value in values)
    plain_lines.extend(("", "תודה."))
    body = "\r\n".join(plain_lines)

    # Explicit RTL HTML is legible in Hebrew Outlook, including Latin IP/VDOM.
    rows = "".join(
        '<tr><td style="padding:3px 0 3px 16px;vertical-align:top;'
        'font-weight:600;white-space:nowrap">' + escape(name) +
        ':</td><td style="padding:3px 0;vertical-align:top">' +
        escape(value) + '</td></tr>'
        for name, value in values)
    fragment = (
        '<div dir="rtl" style="direction:rtl;text-align:right;'
        'font:11pt Arial,sans-serif;color:#222">'
        '<p>שלום,</p><p>אבקש את טיפול צוות SOC עבור הלקוח הבא:</p>'
        '<table dir="rtl" style="border-collapse:collapse;text-align:right">'
        + rows + '</table><p>תודה.</p></div><br>')
    return SocDraft(subject, body, fragment, info)


def _insert_before_signature(fragment, existing_html):
    """Preserve Outlook's default signature and HTML document structure."""
    html = existing_html or ""
    body_tag = _BODY_TAG.search(html)
    if body_tag:
        return html[:body_tag.end()] + fragment + html[body_tag.end():]
    return fragment + html


class OutlookUnavailable(RuntimeError):
    pass


def open_draft(draft):
    """Display a new UNSENT Outlook compose window; never call Send/Save.

    Classic desktop Outlook: COM CreateItem + Display; the user's signature
    remains in HTMLBody. New Outlook does not expose the classic COM object
    model, so fall back to the Windows registered mailto handler.
    """
    if sys.platform != "win32":
        raise OutlookUnavailable("An Outlook email draft requires Windows.")
    try:
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)  # 0=olMailItem
    except Exception:
        mail = None

    if mail is not None:
        # Display first so the configured Outlook signature is inserted.
        # Any COM failure *after* Display must not launch a duplicate draft.
        try:
            mail.Subject = draft.subject
            mail.Display()
            mail.HTMLBody = _insert_before_signature(draft.html_fragment, mail.HTMLBody)
            return "outlook"
        except Exception as exc:
            raise OutlookUnavailable(
                "Outlook opened but the SOC draft could not be populated. "
                "Review the open Outlook window."
            ) from exc

    try:
        # Works when New Outlook is configured as Windows default email app.
        # No recipients, CC/BCC, attachments or sending are involved.
        link = ("mailto:?subject=" + quote(draft.subject, safe="") +
                "&body=" + quote(draft.body, safe=""))
        os.startfile(link)
        return "default_mail"
    except (OSError, AttributeError) as exc:
        raise OutlookUnavailable(
            "Could not open Outlook. Install/sign into Outlook or configure "
            "Outlook as the default Windows email application."
        ) from exc

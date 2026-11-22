"""Compact, lossless Pocket Extra selected-row presentation.

This is display-only: never writes to Excel/SQLite or changes search results.
Fields not shown in the concise overview remain in their original sheet order
under the optional disclosure. FortiGate IP is derived from the worksheet,
not from the customer's public IP address.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from . import extra_soc_outlook as soc

_COLUMN = re.compile(r"\s*\([A-Z]{1,3}\)\s*$", re.IGNORECASE)
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class SummaryCell:
    label: str
    value: str
    field_index: int | None = None


@dataclass(frozen=True)
class RowOverview:
    sheet: str
    row: int
    customer: SummaryCell
    pairs: tuple[tuple[SummaryCell, SummaryCell], ...]
    remaining: tuple[tuple[str, str], ...]


def _header(text):
    label = unicodedata.normalize("NFKC", _COLUMN.sub("", str(text))).casefold()
    return _SPACES.sub(" ", label.strip())


def _find(fields, names, *, prefixes=(), forbidden=()):
    """Recognize headers, not coincidental values from other columns."""
    normalized = tuple((_header(key), str(value).strip())
                       for key, value in fields)
    for name in names:
        for index, (heading, value) in enumerate(normalized):
            if value and heading == name and not any(f in heading for f in forbidden):
                return index
    for prefix in prefixes:
        for index, (heading, value) in enumerate(normalized):
            if value and heading.startswith(prefix) and not any(
                    f in heading for f in forbidden):
                return index
    return None


def row_overview(hit) -> RowOverview:
    """Build a quick view plus every not-yet-shown populated Excel column."""
    fields = tuple((str(k), str(v)) for k, v in hit.fields)
    used = set()

    def choose(label, names=(), *, prefixes=(), forbidden=(), fallback="—"):
        index = _find(fields, names, prefixes=prefixes, forbidden=forbidden)
        if index is not None and index not in used:
            used.add(index)
            return SummaryCell(label, fields[index][1], index)
        return SummaryCell(label, fallback)

    customer = choose(
        "לקוח",
        ("לקוח", "שם לקוח", "שם הלקוח", "שם עסק", "שם העסק", "שם חברה",
         "חברה", "customer", "customer name", "client",
         "business", "business name"))
    circuit = choose(
        "קוד קישור",
        ("קוד קישור", "קוד קו", "מספר קו", "מס קו", "מספר קישור",
         "מס קישור", "מספר קו לקוח", "line code", "line number",
         "circuit id", "circuit code"),
        forbidden=("קבוצה", "group"))
    group = choose(
        "קוד קבוצה",
        ("קוד קבוצה", "קוד קבוצה א", "group code", "group id"),
        prefixes=("קוד קבוצה ", "group code "))
    vdom = choose(
        "VDOM",
        ("vdom", "שם vdom", "vdom name", "vdom id",
         "vdom לקוח", "vdom customer"))
    vrf = choose("VRF", ("vrf", "שם vrf", "vrf name"))
    fg_ip = SummaryCell("FortiGate IP",
                        soc.fortigate_ip_from_sheet(hit.sheet) or "—")
    vlan = choose(
        "VLAN FG",
        ("vlan fg", "fg vlan", "vlan fortigate", "vlan forti"))
    remaining = tuple(value for index, value in enumerate(fields)
                      if index not in used)
    return RowOverview(
        sheet=str(hit.sheet), row=int(hit.row), customer=customer,
        pairs=((circuit, group), (vdom, vrf), (fg_ip, vlan)),
        remaining=remaining)

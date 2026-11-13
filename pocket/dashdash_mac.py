"""Opt-in remote MAC vendor lookup using DashDash's hosted OUI registry.

The request is sent only when the user selects DashDash and clicks Check vendors.
No MACs are uploaded when using Local mode.
"""
from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request
from .windows_proxy_urlopen import urlopen

from . import network_tools as net

DASHDASH_MAC_URL = "https://dashdash-tau.vercel.app/api/mac-lookup"
REMOTE_MAX_MACS = 100
REQUEST_TIMEOUT = 12
MAX_RESPONSE_BYTES = 65536


def parse_remote_macs(text: str) -> list[str]:
    """Normalize unique, explicitly provided MAC addresses for the API."""
    if not isinstance(text, str) or len(text) > 10000:
        raise ValueError("Paste up to 100 MAC addresses.")
    tokens = [token for token in re.split(r"[,;\s]+", text.strip()) if token]
    if not tokens:
        raise ValueError("Paste at least one MAC address.")
    if len(tokens) > REMOTE_MAX_MACS:
        raise ValueError("DashDash accepts up to 100 MAC addresses per request.")
    normalized = set()
    result = []
    for token in tokens:
        try:
            mac = net.normalize_mac(token)
        except ValueError as exc:
            raise ValueError(f"Invalid MAC address: {token[:32]}") from exc
        if mac not in normalized:
            normalized.add(mac)
            result.append(":".join(mac[i:i+2] for i in range(0, 12, 2)))
    return result


def lookup_remote_macs(macs: list[str]) -> list[dict]:
    """Perform one HTTPS POST and validate every returned MAC/vendor record."""
    if not isinstance(macs, list) or not 1 <= len(macs) <= REMOTE_MAX_MACS:
        raise ValueError("DashDash accepts 1–100 MAC addresses per request.")
    keys = []
    for item in macs:
        try:
            keys.append(net.normalize_mac(item))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError("Invalid MAC address sent to DashDash.") from exc
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate MAC addresses in remote request.")
    request = Request(
        DASHDASH_MAC_URL, method="POST",
        data=json.dumps({"macs": macs}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "PocketDesk (manual MAC lookup)"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            if response.status != 200:
                raise ValueError(f"DashDash returned HTTP {response.status}.")
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 429:
            raise ValueError("DashDash is limiting requests. Try again later.") from exc
        raise ValueError(f"DashDash MAC lookup returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ValueError(f"Cannot reach DashDash via Windows proxy/PAC: {exc}. Switch to Local or ask IT.") from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("DashDash returned an unexpectedly large MAC response.")
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("DashDash returned invalid JSON.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("DashDash returned an invalid MAC response.")
    rows = data["results"]
    if len(rows) != len(keys):
        raise ValueError("DashDash returned an incomplete MAC result.")
    parsed = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("DashDash returned an invalid MAC result.")
        try:
            mac_key = net.normalize_mac(row.get("mac"))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError("DashDash returned an invalid MAC address.") from exc
        vendor, registry = row.get("vendor"), row.get("registry")
        if (mac_key not in keys or mac_key in parsed or not isinstance(vendor, str)
                or not vendor.strip() or len(vendor) > 256 or
                not isinstance(registry, str) or len(registry) > 40):
            raise ValueError("DashDash returned an invalid MAC result.")
        parsed[mac_key] = (vendor, registry)
    return [{"input": original, "mac": original, "vendor": parsed[key][0],
             "registry": parsed[key][1]}
            for original, key in zip(macs, keys)]

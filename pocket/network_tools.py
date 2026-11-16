"""Network diagnostics for PocketDesk. Standard library only.

Port checks are TCP connect tests of explicit ports on one IP.
MAC manufacturer data is downloaded from IEEE once, then searched offline.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import gzip
import zlib
from urllib.error import HTTPError, URLError
import errno
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import time
from urllib.request import Request, urlopen

COMMON_PORTS = (
    (21, "FTP"), (22, "SSH"), (23, "Telnet"), (25, "SMTP"),
    (53, "DNS"), (80, "HTTP"), (110, "POP3"), (143, "IMAP"),
    (443, "HTTPS"), (445, "SMB"), (3389, "RDP"), (5900, "VNC"),
    (8080, "HTTP-alt"), (8443, "HTTPS-alt"), (8291, "WinBox"), (8728, "RouterOS API"),
)
PORT_NAMES = {port: label for port, label in COMMON_PORTS}

# Authoritative IEEE Registration Authority public downloads, not a hosted lookup API.
IEEE_LISTS = (
    ("MA-L", "https://standards-oui.ieee.org/oui/oui.csv", 6),
    ("MA-M", "https://standards-oui.ieee.org/oui28/mam.csv", 7),
    ("MA-S", "https://standards-oui.ieee.org/oui36/oui36.csv", 9),
    ("IAB", "https://standards-oui.ieee.org/iab/iab.csv", 9),
)
MAX_MAC_BATCH = 5000
MAX_PORTS = 128


def parse_target(raw: str) -> str:
    """Accept one IPv4/IPv6 address, not a subnet or scan range."""
    try:
        return str(ipaddress.ip_address(raw.strip()))
    except ValueError as exc:
        raise ValueError("Enter a single valid IPv4 or IPv6 address (not a subnet).") from exc


def parse_ports(raw: str, *, max_ports=MAX_PORTS) -> list[int]:
    """Accept comma/space-separated TCP ports and short inclusive ranges."""
    tokens = [t for t in re.split(r"[,\s;]+", raw.strip()) if t]
    if not tokens:
        raise ValueError("Enter at least one TCP port.")
    values = set()
    for token in tokens:
        if "-" in token:
            parts = token.split("-")
            if len(parts) != 2 or not all(x.isdecimal() for x in parts):
                raise ValueError(f"Invalid port range: {token}")
            start, end = map(int, parts)
            if not 1 <= start <= end <= 65535:
                raise ValueError(f"Invalid port range: {token}")
            if end - start + 1 > max_ports or len(values) + end - start + 1 > max_ports:
                raise ValueError(f"A check is limited to {max_ports} TCP ports.")
            values.update(range(start, end + 1))
        elif token.isdecimal() and 1 <= int(token) <= 65535:
            values.add(int(token))
        else:
            raise ValueError(f"Invalid TCP port: {token}")
        if len(values) > max_ports:
            raise ValueError(f"A check is limited to {max_ports} TCP ports.")
    return sorted(values)


def check_tcp_port(ip: str, port: int, timeout: float = 0.8) -> dict:
    """TCP connect() status. An open TCP port does not prove an application is healthy."""
    address = ipaddress.ip_address(ip)
    family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
    destination = (str(address), port, 0, 0) if family == socket.AF_INET6 else (str(address), port)
    started = time.monotonic()
    status = "Error"
    try:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(destination)
            status = "OPEN"
    except ConnectionRefusedError:
        status = "CLOSED"
    except (socket.timeout, TimeoutError):
        status = "TIMEOUT"
    except OSError as exc:
        if exc.errno in {errno.ECONNREFUSED, 10061}:
            status = "CLOSED"
        elif exc.errno in {errno.ETIMEDOUT, 10060, errno.EHOSTUNREACH, errno.ENETUNREACH, 10065, 10051}:
            status = "TIMEOUT"
        else:
            status = "ERROR"
    return {"port": port, "service": PORT_NAMES.get(port, "—"),
            "status": status, "ms": round((time.monotonic() - started) * 1000)}


def scan_tcp_ports(ip: str, ports: list[int], *, timeout: float = 0.8, cancel=None):
    """Yield results as they arrive; caller must run this in a worker thread."""
    if not ports:
        return
    with ThreadPoolExecutor(max_workers=min(12, len(ports))) as pool:
        pending = {pool.submit(check_tcp_port, ip, port, timeout): port for port in ports}
        for future in as_completed(pending):
            if cancel is not None and cancel.is_set():
                for task in pending:
                    task.cancel()
                break
            yield future.result()


def parse_ieee_csv(content: bytes, expected_registry: str, prefix_size: int) -> dict:
    try:
        content = content.decode("utf-8-sig")
        records = csv.DictReader(io.StringIO(content))
        if not set(("Assignment", "Organization Name")).issubset(records.fieldnames or []):
            raise ValueError(f"IEEE {expected_registry} returned unexpected CSV columns")
        result = {}
        for item in records:
            prefix = re.sub(r"[^0-9A-Fa-f]", "", item.get("Assignment") or "").upper()
            organization = (item.get("Organization Name") or "").strip()
            if len(prefix) == prefix_size and organization:
                result[prefix] = [organization, expected_registry]
        if not result:
            raise ValueError(f"IEEE {expected_registry} returned no valid assignments")
        return result
    except UnicodeError as exc:
        raise ValueError(f"IEEE {expected_registry} returned invalid UTF-8") from exc


def download_ieee_database(path: Path, on_progress=None, *, use_windows_proxy=None) -> int:
    """Download complete registries to a temporary set before atomically replacing cache.

    Only fixed HTTPS IEEE origins are used. Never transmit MAC addresses.
    """
    # Restore IEEE's original urllib transport when Windows Proxy is OFF.
    # The explicit ProxyHandler({}) route broke certificate validation on
    # some managed workstations where the previous urllib opener worked.
    # urllib may use its normal OS/environment proxy discovery; this is
    # intentional compatibility behavior for IEEE only. Never disable TLS.
    if use_windows_proxy is True:
        from .ieee_https import open_ieee
        opener = open_ieee
    else:
        opener = urlopen
    merged = {}
    for registry, url, nibbles in IEEE_LISTS:
        if on_progress:
            on_progress(f"Downloading {registry} assignments…")
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 PocketDesk/1.1 (local OUI cache)",
                                        "Accept": "text/csv,*/*;q=0.7"})
        try:
            with opener(request, timeout=25) as response:
                # Read with an upper bound; a full registry is several MB.
                content = response.read(30_000_001)
                headers = getattr(response, "headers", {})
                encoding = (headers.get("Content-Encoding", "") or "").lower()
        except HTTPError as exc:
            if exc.code in (403, 418, 429):
                raise ValueError(
                    f"IEEE {registry} blocked automated downloads (HTTP {exc.code}). "
                    "Use Import CSV with the official IEEE registry files."
                ) from exc
            raise ValueError(f"IEEE {registry} download failed (HTTP {exc.code})") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ValueError(f"IEEE {registry} download failed: {exc}") from exc
        if len(content) > 30_000_000:
            raise ValueError(f"IEEE {registry} file is unexpectedly large")
        if encoding == "gzip":
            content = gzip.decompress(content)
        elif encoding == "deflate":
            content = zlib.decompress(content)
        if len(content) > 30_000_000:
            raise ValueError(f"IEEE {registry} file is unexpectedly large")
        parsed = parse_ieee_csv(content, registry, nibbles)
        # IAB and MA-S share 36-bit address space; prefer current MA-S if duplicated.
        for prefix, vendor in parsed.items():
            merged.setdefault(prefix, vendor)
    if on_progress:
        on_progress("Saving local vendor database…")
    _store_vendor_database(path, merged)
    return len(merged)


def _store_vendor_database(path: Path, merged: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(".tmp")
    try:
        with staged.open("w", encoding="utf-8") as handle:
            json.dump({"updated": time.strftime("%Y-%m-%d"), "vendors": merged}, handle,
                      ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def import_ieee_csv_files(files: list[Path], path: Path) -> int:
    """Import downloaded IEEE CSV files manually if IEEE blocks scripted access."""
    if not files:
        raise ValueError("Select at least one IEEE public registry CSV file.")
    merged, _ = load_vendor_database(path)
    merged = dict(merged)
    total = 0
    lengths = {registry: nibbles for registry, _, nibbles in IEEE_LISTS}
    for file in files:
        with Path(file).open("rb") as handle:
            source = handle.read(30_000_001)
        if len(source) > 30_000_000:
            raise ValueError(f"{Path(file).name} is too large for an IEEE registry CSV")
        try:
            rows = csv.DictReader(io.StringIO(source.decode("utf-8-sig")))
            if not {"Registry", "Assignment", "Organization Name"}.issubset(rows.fieldnames or []):
                raise ValueError("missing IEEE registry columns")
            loaded = 0
            for row in rows:
                registry = (row.get("Registry") or "").strip()
                prefix = re.sub(r"[^0-9A-Fa-f]", "", row.get("Assignment") or "").upper()
                organization = (row.get("Organization Name") or "").strip()
                if registry not in lengths or len(prefix) != lengths[registry] or not organization:
                    continue
                if registry != "IAB" or prefix not in merged or merged[prefix][1] == "IAB":
                    merged[prefix] = [organization, registry]
                loaded += 1
            if not loaded:
                raise ValueError("no recognized IEEE MAC assignments")
            total += loaded
        except UnicodeError as exc:
            raise ValueError(f"{Path(file).name} is not UTF-8 CSV") from exc
        except ValueError as exc:
            raise ValueError(f"Invalid file {Path(file).name}: {exc}") from exc
    _store_vendor_database(path, merged)
    return total


def load_vendor_database(path: Path):
    if not path.exists():
        return {}, "Not downloaded"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("vendors"), dict):
            raise ValueError("Invalid vendor database")
        return data["vendors"], str(data.get("updated", "Unknown date"))
    except (OSError, ValueError, UnicodeError):
        return {}, "Invalid vendor database — update required"


def normalize_mac(text: str) -> str:
    raw = text.strip()
    if re.fullmatch(r"(?i)[0-9a-f]{12}", raw):
        return raw.upper()
    if re.fullmatch(r"(?i)([0-9a-f]{2}[:-]){5}[0-9a-f]{2}", raw):
        if (":" in raw) and ("-" in raw):
            raise ValueError("Mixed MAC separators")
        return raw.replace(":", "").replace("-", "").upper()
    if re.fullmatch(r"(?i)[0-9a-f]{4}(\.[0-9a-f]{4}){2}", raw):
        return raw.replace(".", "").upper()
    raise ValueError("Invalid EUI-48 MAC address")



# Match complete MAC-shaped tokens, not arbitrary words from CLI output.
# The stricter normalizer below still rejects mixed separators/non-hex data.
_MAC_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9:._/-])"
    r"((?:[A-Za-z0-9]{2}[:-]){5}[A-Za-z0-9]{2}|"
    r"(?:[A-Za-z0-9]{4}\.){2}[A-Za-z0-9]{4}|"
    r"[0-9A-Fa-f]{12})"
    r"(?![A-Za-z0-9:._/-])"
)
MAX_MAC_INPUT_CHARS = 2_000_000


def parse_mac_input(raw_text: str, *, limit: int = MAX_MAC_BATCH) -> dict:
    """Extract only complete EUI-48 addresses from pasted MACs or CLI tables.

    Ignore headers, VLANs, interface names, IPv4/IPv6 addresses, port numbers
    and other output. Deduplicate in first-seen order. Invalid *MAC-shaped*
    tokens are counted but never looked up or uploaded. Limit applies to
    unique valid MACs, not unrelated pasted words or repeated MACs.
    """
    if not isinstance(raw_text, str):
        raise ValueError("Paste MAC addresses or a device MAC table.")
    if len(raw_text) > MAX_MAC_INPUT_CHARS:
        raise ValueError("MAC table output is too large; paste a smaller selection.")
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("MAC batch limit must be positive.")
    seen, macs = set(), []
    duplicates = invalid = 0
    for match in _MAC_CANDIDATE.finditer(raw_text):
        token = match.group(1)
        try:
            key = normalize_mac(token)
        except ValueError:
            invalid += 1
            continue
        if key in seen:
            duplicates += 1
            continue
        if len(macs) >= limit:
            raise ValueError(f"Found more than {limit:,} unique MAC addresses; narrow the input.")
        seen.add(key)
        macs.append(":".join(key[i:i + 2] for i in range(0, 12, 2)))
    if not macs:
        raise ValueError("No valid MAC addresses found. IP addresses, port numbers and CLI text are ignored.")
    return {"macs": macs, "duplicates": duplicates, "invalid": invalid}


def port_result_sort_key(row: dict) -> tuple[int, int]:
    """Keep OPEN at the top, followed by CLOSED then TIMEOUT, by port number."""
    rank = {"OPEN": 0, "CLOSED": 1, "TIMEOUT": 2}
    return (rank.get(row.get("status"), 3), int(row.get("port", 0)))


def mac_lookup(raw: str, vendors: dict) -> dict:
    try:
        normalized = normalize_mac(raw)
    except ValueError:
        return {"input": raw, "mac": "—", "vendor": "Invalid MAC", "registry": "—"}
    pretty = ":".join(normalized[i:i+2] for i in range(0, 12, 2))
    first = int(normalized[:2], 16)
    if first & 1:
        organization, registry = "Multicast / group address", "Special"
    elif first & 2:
        organization, registry = "Locally administered / randomized", "Special"
    elif not vendors:
        organization, registry = "Database not downloaded", "—"
    else:
        record = next((vendors[normalized[:length]] for length in (9, 7, 6)
                       if normalized[:length] in vendors), None)
        organization, registry = record if record else ("Unknown / unregistered", "—")
    return {"input": raw, "mac": pretty, "vendor": organization, "registry": registry}


def batch_lookup(raw_text: str, vendors: dict, limit=MAX_MAC_BATCH):
    """Lookup complete, unique MACs only; never treat CLI column text as MACs."""
    parsed = parse_mac_input(raw_text, limit=limit)
    return [mac_lookup(mac, vendors) for mac in parsed["macs"]]


def export_csv(path: Path, columns: list[str], results: list[dict]):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for result in results:
            # Avoid Excel/Calc interpreting untrusted exported input as formulas.
            writer.writerow({key: ("'" + value if isinstance(value, str) and
                                   value.startswith(("=", "+", "-", "@", "\t", "\r")) else value)
                             for key, value in result.items() if key in columns})

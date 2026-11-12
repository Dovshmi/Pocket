"""Build the offline MAC vendor cache used by PocketDesk (no Python on client).

Public IEEE MA-L, MA-M, MA-S and IAB assignment snapshot, mirrored by
Ringmast4r/OUI-Master-Database. Only current IEEE registration records are
included; CID is excluded because it is not a MAC address allocation.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen
from collections import Counter
import hashlib

SOURCE = (
    "https://raw.githubusercontent.com/Ringmast4r/"
    "OUI-Master-Database/master/LISTS/master_oui.csv"
)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist"
WIDTHS = {"MA-L": 6, "MA-M": 7, "MA-S": 9, "IAB": 9}

def build():
    req = Request(SOURCE, headers={"User-Agent": "PocketDesk-offline-registry-pack/1.0"})
    with urlopen(req, timeout=120) as resp:
        raw = resp.read(25_000_001)
    if len(raw) > 25_000_000:
        raise ValueError("Registry mirror response exceeds size limit")
    if not raw:
        raise ValueError("Empty registry mirror response")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    required = {"oui", "manufacturer", "registry", "status", "sources"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError(f"Unexpected CSV columns: {reader.fieldnames}")
    vendors = {}
    counts = Counter()
    for row in reader:
        registry = (row.get("registry") or "").strip()
        if registry not in WIDTHS:
            continue
        # Exclude deleted/historical records and community-only guesses.
        if (row.get("status") or "").strip().lower() != "current":
            continue
        if "IEEE" not in (row.get("sources") or "").upper().split("+"):
            continue
        prefix = re.sub(r"[^0-9A-Fa-f]", "", row.get("oui") or "").upper()
        name = (row.get("registrant_raw") or row.get("manufacturer") or "").strip()
        if len(prefix) != WIDTHS[registry] or not name:
            continue
        # 36-bit current MA-S wins over its legacy IAB counterpart.
        if prefix in vendors and vendors[prefix][1] == "MA-S" and registry == "IAB":
            continue
        if prefix not in vendors:
            counts[registry] += 1
        vendors[prefix] = [name, registry]

    if len(vendors) < 55_000 or counts["MA-L"] < 39_000 or counts["MA-M"] < 6_000 or counts["MA-S"] < 6_500 or counts["IAB"] < 4_000:
        raise AssertionError(f"Partial data blocked: {len(vendors)} entries, {dict(counts)}")
    OUT.mkdir(exist_ok=True)
    output = OUT / "vendors.json"
    output.write_text(json.dumps(
        {"updated": datetime.now(timezone.utc).date().isoformat(), "vendors": vendors},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    decoded = json.loads(output.read_text(encoding="utf-8"))
    assert decoded["vendors"] == vendors
    for prefix, (name, registry) in decoded["vendors"].items():
        assert len(prefix) == WIDTHS[registry]
        assert name
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (OUT / "vendors-SHA256.txt").write_text(
        f"{digest}  vendors.json\n", encoding="ascii")
    (OUT / "vendors-README.txt").write_text(
        "PocketDesk offline MAC manufacturer database\n"
        f"Assignments: {len(vendors)}\n"
        f"Registry breakdown: {dict(counts)}\n"
        f"Generated (UTC): {datetime.now(timezone.utc).date().isoformat()}\n"
        "Source: Public IEEE MA-L/MA-M/MA-S/IAB snapshot mirrored at\n"
        f"{SOURCE}\n"
        "Usage: place vendors.json in Pocket-Portable/data/ beside data.json\n"
        "Restart PocketDesk.exe. No app download is required.\n"
        "Only current IEEE entries are retained; CID and history excluded.\n",
        encoding="utf-8")
    print(f"PASS: built offline {output} with {len(vendors)} current IEEE prefixes")
    print(f"SHA256: {digest}")
    print(f"Breakdown: {dict(counts)}")

if __name__ == "__main__":
    build()

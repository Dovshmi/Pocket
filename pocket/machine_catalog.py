"""Machine catalogue and safe merging of local and built-in command references."""
import json
from pathlib import Path

def load_catalog(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = data.get("machines", []) if isinstance(data, dict) else []
    if not isinstance(rows, list):
        return []
    seen, names = set(), []
    for row in rows:
        if isinstance(row, str) and 1 <= len(row.strip()) <= 90:
            label = row.strip()
            if label.casefold() not in seen:
                names.append(label)
                seen.add(label.casefold())
    return names

def machine_names(commands, catalog):
    found = {label.casefold(): label for label in catalog}
    for item in commands:
        label = item.get("machine")
        if isinstance(label, str) and label.strip():
            found.setdefault(label.casefold(), label.strip())
    return sorted(found.values(), key=str.casefold)

def combine_references(*libraries):
    seen_ids, seen_commands, combined = set(), set(), []
    for library in libraries:
        for item in library:
            identity = item["id"]
            signature = (item["machine"].casefold().strip(),
                         " ".join(item["command"].casefold().split()))
            if identity in seen_ids or signature in seen_commands:
                continue
            seen_ids.add(identity)
            seen_commands.add(signature)
            combined.append(item)
    return combined

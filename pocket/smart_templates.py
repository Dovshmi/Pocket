"""Optional, offline, copy-only CLI command templates for Pocket.

Existing commands are *always* plain commands until a user explicitly saves
template metadata. Suggestions are only drafts and never touch the library.
The original CLI text remains untouched for search, editing and plain copying.
"""
from __future__ import annotations

import ipaddress
import re

VERSION = 1
MAX_FIELDS = 12
MAX_TEMPLATE_LENGTH = 6000
MAX_VALUE_LENGTH = 250
FIELD_TYPES = (
    "text", "ipv4", "ipv6", "cidr", "ipv6_cidr", "port", "vlan",
    "integer", "interface", "vrf", "mac", "choice",
)
TOKEN = re.compile(r"\{\{([A-Za-z][A-Za-z0-9_]{0,31})\}\}")
FIELD_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}\Z")
SOURCE_HINTS = re.compile(
    r"(?<!\{)\{(?P<brace>[A-Za-z][\w -]{0,35})\}(?!\})"
    r"|<(?P<angle>[^<>\n]{1,44})>"
    r"|\[(?P<square>[^\[\]\n]{1,48})\]"
    r"|(?P<ip>[xX]\.[xX]\.[xX]\.[xX])(?:\s*\((?P<ipnote>start|end|source|destination|lan|wan)\))?"
    r"|(?P<star>\*[A-Za-z][A-Za-z0-9_-]{1,23}\*)"
    r"|(?P<interface>\bx/x(?:/x)?\b)"
)
MAC = re.compile(r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\Z")
DEVICE_NAME = re.compile(r"[A-Za-z0-9_./:@-]+\Z")
RISK_MARKERS = (" -> ", " --> ", " || ", " // ", " ??? ")


def field_names(text: str) -> list[str]:
    """Ordered, unique names from explicit {{NAME}} markers."""
    if not isinstance(text, str):
        return []
    return list(dict.fromkeys(TOKEN.findall(text)))


def _guess_type(label: str) -> str:
    key = label.casefold().strip()
    if any(x in key for x in ("cidr", "prefix", "subnet")):
        return "cidr"
    if "ipv6" in key:
        return "ipv6"
    if "mac" in key:
        return "mac"
    if any(x in key for x in ("vlan", "svlan", "cvlan")):
        return "vlan"
    if "vrf" in key or "routing instance" in key:
        return "vrf"
    if any(x in key for x in ("interface", "int-name", "physical port", "ממשק", "uplink")):
        return "interface"
    if any(x in key for x in ("port number", "portnumber", "tcp port", "udp port")):
        return "port"
    if any(x in key for x in ("ip", "כתובת", "wan", "gateway", "neighbor")):
        return "ipv4"
    if any(x in key for x in ("number", "count", "repeat", "size", "num")):
        return "integer"
    return "text"


def _unique_name(label: str, counts: dict[str, int], *, can_reuse: bool) -> str:
    clean = re.sub(r"[^A-Za-z0-9_]+", "_", label.upper()).strip("_")
    clean = clean[:25] if clean and clean[0].isalpha() else "VALUE"
    if can_reuse and clean in counts:
        return clean
    counts[clean] = counts.get(clean, 0) + 1
    return clean if counts[clean] == 1 else clean + "_" + str(counts[clean])


def suggest_template(command: str) -> dict | None:
    """Conservative, review-only suggestion; does not alter the original.

    Generic occurrences of x.x.x.x are deliberately kept distinct. Repeating
    an explicit {vrf} name instead reuses a shared field. Fixed IPs/numbers
    are never silently treated as variables.
    """
    if not isinstance(command, str) or not command.strip():
        return None
    matches = []
    for match in SOURCE_HINTS.finditer(command):
        kind = match.lastgroup
        # For the x.x.x.x note pattern lastgroup is ipnote, not ip.
        kind = "ip" if match.group("ip") is not None else kind
        raw = match.group(0)
        if kind == "square":
            value = match.group("square").strip()
            # Brackets sometimes describe literal alternatives, not a value.
            if not any(ch.isalpha() for ch in value) or "|" in value or value.count("/") > 1:
                continue
        elif kind == "angle":
            value = match.group("angle").strip()
            if not any(ch.isalpha() for ch in value):
                continue
        elif kind == "brace":
            value = match.group("brace").strip()
        elif kind == "ip":
            value = (match.group("ipnote") or "IP").strip()
            if value.lower() in ("start", "end", "source", "destination"):
                value = value.upper() + "_IP"
        elif kind == "star":
            value = match.group("star").strip("*")
        elif kind == "interface":
            value = "INTERFACE"
        else:
            continue
        matches.append((match.start(), match.end(), value, kind, raw))
    if not matches:
        return None

    chunks = []
    fields = []
    known = {}
    counts = {}
    current = 0
    for start, stop, label, kind, raw in matches:
        # Avoid replacing overlapping hints (for example marker text inside a bracket).
        if start < current:
            continue
        keep_shared = kind == "brace"
        name = _unique_name(label, counts, can_reuse=keep_shared)
        chunks.append(command[current:start])
        chunks.append("{{" + name + "}}")
        if name not in known:
            fields.append({"name": name, "label": label.replace("_", " ").strip().title(),
                           "type": "interface" if kind == "interface" else _guess_type(label)})
            known[name] = True
        current = stop
    chunks.append(command[current:])
    formatted = "".join(chunks)
    if formatted == command or len(fields) > MAX_FIELDS:
        return None
    warnings = ["Review all suggested fields and syntax before saving."]
    if any(token in command for token in RISK_MARKERS):
        warnings.append("This entry may contain instructions or alternatives, not a single CLI command.")
    if any(ch in command for ch in "[]()"):
        warnings.append("Review bracketed explanations that may remain in the generated command.")
    return {"version": VERSION, "source_command": command,
            "format": formatted, "fields": fields, "warnings": warnings}


def default_fields(formatted: str, existing=None) -> list[dict]:
    """Keep settings for existing names while syncing a hand-edited format."""
    old = {row.get("name"): row for row in (existing or [])
           if isinstance(row, dict) and isinstance(row.get("name"), str)}
    return [
        {"name": name, "label": str(old.get(name, {}).get("label") or name.replace("_", " ").title()),
         "type": str(old.get(name, {}).get("type") or _guess_type(name)),
         **({"options": list(old[name]["options"])}
            if name in old and isinstance(old[name].get("options"), list) else {})}
        for name in field_names(formatted)
    ]


def validate_template(template: dict, source_command: str) -> dict:
    """Return schema-safe metadata, rejecting malformed or ambiguous formats."""
    if not isinstance(template, dict) or not isinstance(source_command, str):
        raise ValueError("Invalid template or source command.")
    formatted = template.get("format")
    if not isinstance(formatted, str) or not formatted.strip() or len(formatted) > MAX_TEMPLATE_LENGTH:
        raise ValueError("Template must contain 1 to 6000 characters.")
    if any(ord(ch) < 32 and ch not in "\n\t\r" for ch in formatted):
        raise ValueError("Template has unsupported control characters.")
    names = field_names(formatted)
    if not names or len(names) > MAX_FIELDS:
        raise ValueError("Templates need 1 to 12 {{FIELD}} placeholders.")
    # No malformed {{...}} / undeclared markers can silently leak into output.
    if "{{" in TOKEN.sub("", formatted) or "}}" in TOKEN.sub("", formatted):
        raise ValueError("Invalid placeholder: use {{NAME}} with letters, digits and underscores.")
    fields = template.get("fields")
    if not isinstance(fields, list) or len(fields) != len(names):
        raise ValueError("Field definitions must match placeholders in the template.")
    defined = {}
    clean_fields = []
    for f in fields:
        if not isinstance(f, dict) or not isinstance(f.get("name"), str):
            raise ValueError("Malformed template field.")
        name = f["name"]
        if not FIELD_NAME.fullmatch(name) or name not in names or name in defined:
            raise ValueError("Duplicate or unknown template field: " + name)
        label = f.get("label")
        kind = f.get("type")
        if not isinstance(label, str) or not (1 <= len(label.strip()) <= 80):
            raise ValueError("A template field needs a label up to 80 characters.")
        if kind not in FIELD_TYPES:
            raise ValueError("Unknown template field type for " + name)
        row = {"name": name, "label": label.strip(), "type": kind}
        if kind == "choice":
            options = f.get("options")
            if (not isinstance(options, list) or not 2 <= len(options) <= 30
                    or any(not isinstance(v, str) or not v.strip() or len(v) > 100
                           or "\n" in v or "\r" in v for v in options)
                    or len(set(options)) != len(options)):
                raise ValueError("Choice fields require 2 to 30 distinct options.")
            row["options"] = list(options)
        clean_fields.append(row)
        defined[name] = True
    if set(defined) != set(names):
        raise ValueError("Some placeholders have no matching field definition.")
    # Save in occurrence order, not whatever order controls were drawn.
    by_name = {f["name"]: f for f in clean_fields}
    return {"version": VERSION, "source_command": source_command,
            "format": formatted, "fields": [by_name[n] for n in names]}


def template_state(command_row: dict) -> str:
    """Plain, configured, or needs-review if original command changed."""
    template = command_row.get("template") if isinstance(command_row, dict) else None
    if not isinstance(template, dict):
        return "plain"
    if template.get("version") != VERSION:
        return "needs_review"
    if template.get("source_command") != command_row.get("command"):
        return "needs_review"
    try:
        validate_template(template, command_row["command"])
    except (KeyError, ValueError, TypeError):
        return "needs_review"
    return "configured"


def validate_value(field: dict, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Enter a text value.")
    value = value.strip()
    if not value or len(value) > MAX_VALUE_LENGTH:
        raise ValueError("Enter a value between 1 and 250 characters.")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("A value must fit on one line and cannot contain control characters.")
    kind = field["type"]
    try:
        if kind == "ipv4":
            if ipaddress.ip_address(value).version != 4:
                raise ValueError("Enter an IPv4 address.")
        elif kind == "ipv6":
            if ipaddress.ip_address(value).version != 6:
                raise ValueError("Enter an IPv6 address.")
        elif kind in ("cidr", "ipv6_cidr"):
            network = ipaddress.ip_network(value, strict=False)
            if network.version != (4 if kind == "cidr" else 6):
                raise ValueError("Enter a network in the expected IP version.")
        elif kind in ("vlan", "port", "integer"):
            if not re.fullmatch(r"[0-9]+", value):
                raise ValueError("Enter a whole number.")
            number = int(value)
            if kind == "vlan" and not 1 <= number <= 4094:
                raise ValueError("VLAN ID must be 1–4094.")
            if kind == "port" and not 1 <= number <= 65535:
                raise ValueError("TCP/UDP port must be 1–65535.")
            if kind == "integer" and number > 2147483647:
                raise ValueError("Number is too large.")
        elif kind in ("interface", "vrf"):
            if not DEVICE_NAME.fullmatch(value):
                raise ValueError("Use letters, digits, _, -, /, ., :, or @.")
        elif kind == "mac":
            if not MAC.fullmatch(value):
                raise ValueError("Enter a MAC address such as aa:bb:cc:dd:ee:ff.")
        elif kind == "choice":
            if value not in field.get("options", ()):
                raise ValueError("Choose an allowed option.")
        elif kind == "text":
            # Free text remains useful for CLI snippets; reject accidental
            # command chaining and multiline injection in generated output.
            if any(op in value for op in (";", "&&", "||", "|", "\x60")):
                raise ValueError("Avoid shell command separators in a field.")
        else:
            raise ValueError("Unsupported field type.")
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    return value


def render_template(command_row: dict, values: dict) -> str:
    """Render exactly the saved format, never run it or store entered values."""
    if template_state(command_row) != "configured":
        raise ValueError("This command has no approved current template.")
    template = validate_template(command_row["template"], command_row["command"])
    if not isinstance(values, dict):
        raise ValueError("Provide values for the template fields.")
    fields = {f["name"]: f for f in template["fields"]}
    checked = {name: validate_value(field, values.get(name))
               for name, field in fields.items()}
    generated = TOKEN.sub(lambda match: checked[match.group(1)], template["format"])
    if "{{" in generated or "}}" in generated:
        raise ValueError("Generated command contains unresolved placeholders.")
    return generated

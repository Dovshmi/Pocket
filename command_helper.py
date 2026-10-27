"""Offline, copy-only command reference functions for PocketDesk.

Packaged commands are sanitized examples. They are never executed by this module.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import unicodedata

ALL_MACHINES = 'All machines'
ALL_CATEGORIES = 'All categories'
MAX_RESULTS = 180


def normalize(value: str) -> str:
    text = unicodedata.normalize('NFKC', str(value or '')).casefold()
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    return re.sub(r'\s+', ' ', text).strip()


def load_library(path: Path) -> list[dict]:
    """Read an explicitly pre-curated command file; never import credentials."""
    try:
        parsed = json.loads(Path(path).read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return []
    records = parsed.get('commands', []) if isinstance(parsed, dict) else []
    if not isinstance(records, list):
        return []
    results = []
    seen = set()
    for row in records:
        if not isinstance(row, dict):
            continue
        fields = ('id', 'machine', 'description', 'command', 'category')
        if not all(isinstance(row.get(key), str) for key in fields):
            continue
        if not row['machine'].strip() or not row['command'].strip() or row['id'] in seen:
            continue
        seen.add(row['id'])
        results.append(row)
    return results


def machines_for(commands: list[dict]) -> list[str]:
    return sorted({item['machine'] for item in commands}, key=lambda name: normalize(name))


def categories_for(commands: list[dict], machine: str = ALL_MACHINES) -> list[str]:
    return sorted({r['category'] for r in commands if machine == ALL_MACHINES or r['machine'] == machine})


def find_commands(commands: list[dict], query='', machine=ALL_MACHINES,
                  category=ALL_CATEGORIES, mode='all', favorites=(), recent=()) -> list[dict]:
    """Each space-delimited query term matches command OR purpose (AND matching).

    Results with a closer command match rank before general matches. Matching is
    case-insensitive and compatible with Hebrew descriptions.
    """
    tokens = normalize(query).split()
    favs = set(favorites)
    recent_pos = {ident: pos for pos, ident in enumerate(recent)}
    matches = []
    for row in commands:
        if machine != ALL_MACHINES and row['machine'] != machine:
            continue
        if category != ALL_CATEGORIES and row['category'] != category:
            continue
        if mode == 'favorites' and row['id'] not in favs:
            continue
        if mode == 'recent' and row['id'] not in recent_pos:
            continue
        command = normalize(row['command'])
        purpose = normalize(row['description'])
        context = normalize(row['machine'] + ' ' + row['category'])
        if not all(t in command or t in purpose or t in context for t in tokens):
            continue
        score = sum(6 if command.startswith(t) else 4 if t in command else
                    3 if purpose.startswith(t) else 2 if t in purpose else 1 for t in tokens)
        if normalize(query) == command:
            score += 40
        if normalize(query) == purpose:
            score += 30
        if row['id'] in favs:
            score += 1
        if mode == 'recent':
            sort_order = (recent_pos[row['id']],)
        else:
            sort_order = (-score, row['description'] == 'Command reference', normalize(row['machine']), normalize(row['description']), normalize(row['command']))
        matches.append((sort_order, row))
    matches.sort(key=lambda x: x[0])
    return [row for _, row in matches]


def updated_recent(previous, ident: str, limit=15):
    return [ident] + [x for x in previous if x != ident][:max(0, limit - 1)]


def safe_prefs(prefs):
    if not isinstance(prefs, dict):
        prefs = {}
    favorites = prefs.get('favorites', [])
    recent = prefs.get('recent', [])
    return {
        'machine': str(prefs.get('machine', ALL_MACHINES)),
        'favorites': [x for x in favorites if isinstance(x, str)][:2000] if isinstance(favorites, list) else [],
        'recent': [x for x in recent if isinstance(x, str)][:15] if isinstance(recent, list) else [],
    }


# User-created commands live in data.json, never in the original private command pack.
MAX_CUSTOM_COMMANDS = 1000
MAX_COMMAND_LENGTH = 6000


def validate_custom_command(machine, category, description, command, *, identifier=None):
    """Validate an offline command entry and return a canonical record.

    The app never executes or interprets command text. Validation is for
    accidental empty/oversized records, not a credential scanner.
    """
    import uuid
    machine, category, description = (str(v).strip() for v in (machine, category, description))
    command = str(command).strip()
    if not machine or machine == ALL_MACHINES or len(machine) > 90:
        raise ValueError('Choose or enter a machine name (up to 90 characters).')
    if not description or len(description) > 250:
        raise ValueError('Enter a short purpose/description (up to 250 characters).')
    if not category or len(category) > 70:
        raise ValueError('Enter a category (up to 70 characters).')
    if not command or len(command) > MAX_COMMAND_LENGTH:
        raise ValueError(f'Enter command text (up to {MAX_COMMAND_LENGTH} characters).')
    if any(ord(c) < 32 and c not in '\n\t\r' for c in command):
        raise ValueError('Command contains unsupported control characters.')
    if identifier is None:
        identifier = 'user:' + uuid.uuid4().hex
    if not isinstance(identifier, str) or not re.fullmatch(r'user:[a-f0-9]{32}', identifier):
        raise ValueError('Invalid custom command ID.')
    return {'id': identifier, 'machine': machine, 'category': category,
            'description': description, 'command': command, 'origin': 'custom'}


def safe_custom_commands(value):
    """Load only well-formed, uniquely identified custom records from disk."""
    if not isinstance(value, list):
        return []
    result = []
    seen = set()
    for item in value[:MAX_CUSTOM_COMMANDS * 2]:
        if not isinstance(item, dict):
            continue
        try:
            entry = validate_custom_command(item.get('machine', ''),
                                            item.get('category', ''),
                                            item.get('description', ''),
                                            item.get('command', ''),
                                            identifier=item.get('id'))
        except ValueError:
            continue
        if entry['id'] not in seen:
            result.append(entry)
            seen.add(entry['id'])
        if len(result) >= MAX_CUSTOM_COMMANDS:
            break
    return result


def merged_commands(bundled, custom):
    """Keep packaged read-only commands separate from user data."""
    seen = {row['id'] for row in bundled}
    return list(bundled) + [row for row in custom if row['id'] not in seen]

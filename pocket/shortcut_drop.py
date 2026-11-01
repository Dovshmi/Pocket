"""Pure, side-effect-free drag-and-drop decoding and shortcut title suggestions.

Dropped content is only used to populate the shortcut form, NEVER auto-saved or launched.
"""

from __future__ import annotations

import configparser
import ntpath
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

from .shortcut_utils import normalize_url


def _local_path(text: str) -> str:
    """Turn a dropped file URI or native path into a native OS path."""
    value = text.strip().strip('"').strip()
    if value.startswith('{') and value.endswith('}'):
        value = value[1:-1]
    if value.lower().startswith('file://'):
        parts = urlsplit(value)
        if parts.scheme.lower() != 'file':
            return value
        if os.name == 'nt':
            # url2pathname decodes /C:/... and converts Unix separators on Windows.
            value = url2pathname(unquote(parts.path))
            if parts.netloc and parts.netloc.lower() != 'localhost':
                value = '\\\\' + parts.netloc + value
        else:
            value = unquote(parts.path)
            if parts.netloc and parts.netloc.lower() != 'localhost':
                value = '//' + parts.netloc + value
    return value


def _best_web_title(url: str) -> str:
    info = urlsplit(url)
    host = (info.hostname or '').lower().removeprefix('www.').removeprefix('m.')
    labels = host.split('.')
    base = labels[-2] if len(labels) > 1 else labels[0]
    known = {'github': 'GitHub', 'youtube': 'YouTube', 'google': 'Google',
             'gmail': 'Gmail', 'stackoverflow': 'Stack Overflow',
             'microsoft': 'Microsoft', 'reddit': 'Reddit', 'wikipedia': 'Wikipedia',
             'gitlab': 'GitLab', 'notion': 'Notion', 'chatgpt': 'ChatGPT'}
    brand = known.get(base, base.replace('-', ' ').title())
    if host == 'mail.google.com':
        return 'Gmail'
    if host.startswith('docs.google.'):
        return 'Google Docs'
    pieces = [unquote(piece) for piece in info.path.split('/') if piece]
    if base in {'github', 'gitlab'} and len(pieces) >= 2:
        return f'{pieces[1][:42]} · {brand}'
    if len(pieces) >= 1 and base not in {'youtube', 'google', 'reddit'}:
        last = pieces[-1]
        if last.lower().endswith(('.html', '.htm', '.php')):
            last = last.rsplit('.', 1)[0]
        if last and len(last) <= 32 and not any(x in last for x in '=;&'):
            return f'{last.replace("-", " ").replace("_", " ")} · {brand}'
    return brand or host


def _site_shortcut(text: str) -> dict:
    url = normalize_url(text)
    info = urlsplit(url)
    # Do not interpret arbitrary dragged text as a URL.
    hostname = info.hostname or ''
    if '.' not in hostname and hostname != 'localhost':
        raise ValueError('Drop a website URL, an existing file, or a folder.')
    return {'kind': 'url', 'url': url, 'title': _best_web_title(url)}


def _single_item(raw: str, splitlist=None) -> str:
    """Handle Windows braced Tcl file lists, spaced paths, and browser URI lists."""
    original = raw.strip()
    if not original:
        raise ValueError('Nothing was dropped.')
    # Preserve literal paths containing spaces before parsing a Tcl file list.
    if Path(_local_path(original)).exists():
        return original
    if original.startswith('{') and original.endswith('}') and Path(_local_path(original)).exists():
        return original
    # Browser drag: text/uri-list can include comments and multiple addresses.
    lines = [s.strip() for s in original.splitlines() if s.strip() and not s.strip().startswith('#')]
    if len(lines) > 1:
        raise ValueError('Please drag one URL, file, or folder at a time.')
    if len(lines) == 1:
        original = lines[0]
    if splitlist is not None and not original.lower().startswith(('http://', 'https://', 'file://')):
        try:
            values = tuple(splitlist(original))
        except (ValueError, TypeError):
            values = ()
        if len(values) > 1:
            # Plain text can contain spaces; do not silently truncate it.
            raise ValueError('Please drag one URL, file, or folder at a time.')
        if len(values) == 1:
            original = values[0]
    return original


def guess_shortcut(raw: str, *, splitlist=None) -> dict:
    """Return {kind,title,url} for an individual drop; no persistence or launch."""
    item = _single_item(raw, splitlist=splitlist)
    path = Path(_local_path(item)).expanduser()
    if path.exists():
        if path.is_dir():
            return {'kind': 'folder', 'title': path.name or str(path), 'url': str(path.resolve())}
        if path.is_file():
            # Windows .url files are Explorer website shortcuts; their target is useful.
            if path.suffix.lower() == '.url':
                parser = configparser.ConfigParser(interpolation=None)
                try:
                    parser.read(path, encoding='utf-8-sig')
                    website = parser.get('InternetShortcut', 'URL')
                    return _site_shortcut(website)
                except (configparser.Error, OSError, KeyError, ValueError):
                    pass  # Keep a usable file shortcut when the .url cannot be parsed.
            return {'kind': 'file', 'title': path.stem or path.name, 'url': str(path.resolve())}
    # Missing absolute paths should not accidentally become web addresses.
    if item.lower().startswith('file://') or ntpath.isabs(item) or item.startswith(('/', '~')):
        raise ValueError('Dropped file or folder does not exist on this PC.')
    return _site_shortcut(item)

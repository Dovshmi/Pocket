"""Deterministic, offline IPv4 subnet calculations for PocketDesk.

No DNS lookups, IP scanning, or network calls are performed.
"""
from __future__ import annotations

from ipaddress import IPv4Address, IPv4Network

MAX_SUBNET_ROWS = 128


def _normalize_ipv4(value: str) -> IPv4Address:
    """Validate a literal IPv4 address, not a hostname or IPv6 address."""
    try:
        return IPv4Address(value.strip())
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Enter a valid IPv4 address (for example 192.168.1.10).") from exc


def calculate(ip: str, prefix: str | int) -> dict:
    """Calculate network details from a host IP + CIDR prefix or dotted subnet mask."""
    addr = _normalize_ipv4(ip)
    if isinstance(prefix, bool):
        raise ValueError("CIDR must be from 0 to 32, or a valid dotted subnet mask.")
    mask = str(prefix).strip().lstrip('/')
    try:
        network = IPv4Network(f"{addr}/{mask}", strict=False)
    except (ValueError, TypeError) as exc:
        raise ValueError("CIDR must be 0–32, or a valid dotted subnet mask.") from exc
    total = network.num_addresses
    if network.prefixlen == 32:
        first = last = network.network_address
        usable = 1
    elif network.prefixlen == 31:
        first, last = network.network_address, network.broadcast_address
        usable = 2
    else:
        first = network.network_address + 1
        last = network.broadcast_address - 1
        usable = total - 2
    return {
        'input_ip': str(addr), 'cidr': network.with_prefixlen, 'network': str(network.network_address),
        'prefix': network.prefixlen, 'mask': str(network.netmask), 'wildcard': str(network.hostmask),
        'broadcast': str(network.broadcast_address), 'first': str(first), 'last': str(last),
        'total': total, 'usable': usable, 'private': addr.is_private,
    }


def split_subnets(network_cidr: str, new_prefix: str | int, *, limit: int = MAX_SUBNET_ROWS) -> dict:
    """Return bounded, ordered child networks without expanding a huge address space."""
    try:
        net = IPv4Network(network_cidr, strict=True)
        prefix = int(str(new_prefix).strip().lstrip('/'))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Provide a valid IPv4 network and new CIDR prefix.") from exc
    if not net.prefixlen <= prefix <= 32:
        raise ValueError(f"New prefix must be from /{net.prefixlen} to /32.")
    if not 1 <= limit <= MAX_SUBNET_ROWS:
        raise ValueError(f"Limit must be between 1 and {MAX_SUBNET_ROWS}.")
    count = 1 << (prefix - net.prefixlen)
    step = 1 << (32 - prefix)
    rows = []
    for i in range(min(count, limit)):
        addr = IPv4Address(int(net.network_address) + i * step)
        item = calculate(str(addr), prefix)
        rows.append({'cidr': item['cidr'], 'usable': item['usable'], 'range':
                     item['first'] if item['first'] == item['last'] else f"{item['first']} – {item['last']}"})
    return {'count': count, 'shown': len(rows), 'rows': rows, 'truncated': count > limit}


def summary_text(details: dict) -> str:
    """Plain-text network summary suitable for notes or a terminal."""
    return '\n'.join([
        f"IP address: {details['input_ip']}",
        f"Network: {details['cidr']}",
        f"Subnet mask: {details['mask']}",
        f"Wildcard: {details['wildcard']}",
        f"Broadcast: {details['broadcast']}",
        f"First usable: {details['first']}",
        f"Last usable: {details['last']}",
        f"Usable addresses: {details['usable']:,}",
        f"Total addresses: {details['total']:,}",
    ])

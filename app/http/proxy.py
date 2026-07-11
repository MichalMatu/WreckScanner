from __future__ import annotations

from functools import lru_cache
from ipaddress import ip_address, ip_network

from app import config


def _client_host(handler) -> str:
    client_address = getattr(handler, "client_address", ("",))
    return str(client_address[0] if client_address else "").strip()


@lru_cache(maxsize=1)
def _trusted_proxy_networks():
    networks = []
    for value in config.TRUSTED_PROXY_ADDRESSES:
        try:
            networks.append(ip_network(value, strict=False))
        except ValueError:
            continue
    return tuple(networks)


def request_from_trusted_proxy(handler) -> bool:
    try:
        client_ip = ip_address(_client_host(handler))
    except ValueError:
        return False
    return any(client_ip in network for network in _trusted_proxy_networks())

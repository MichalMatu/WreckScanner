from __future__ import annotations

import threading

import requests

from core.geo import bbox_4326

_thread_local = threading.local()


def get_http_session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    return session


def get_bbox(lat: float, lon: float, width_m: float, height_m: float) -> str:
    return bbox_4326(lat, lon, width_m, height_m)

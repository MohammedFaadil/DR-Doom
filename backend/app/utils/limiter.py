"""Shared rate limiter (§79) — per-IP by default via slowapi."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

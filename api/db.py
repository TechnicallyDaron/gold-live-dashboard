"""
N-CORE — Supabase PostgREST client. Zero new dependencies (requests only).
Backend uses the service-role key with EXPLICIT user_id filters on every
query (standard server-side pattern; RLS still guards direct client access).
When env is absent, enabled() is False and the store falls back to files.
"""
import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


def enabled() -> bool:
    return bool(SUPABASE_URL and SERVICE_KEY)


def _headers(extra=None):
    h = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}",
         "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    return h


def _url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"


def select(table: str, filters: dict | None = None, order: str | None = None,
           limit: int | None = None) -> list:
    params = {k: f"eq.{v}" for k, v in (filters or {}).items()}
    if order:
        params["order"] = order
    if limit:
        params["limit"] = str(limit)
    r = requests.get(_url(table), headers=_headers(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def insert(table: str, rows) -> list:
    if isinstance(rows, dict):
        rows = [rows]
    r = requests.post(_url(table), headers=_headers({"Prefer": "return=representation"}),
                      json=rows, timeout=10)
    r.raise_for_status()
    return r.json()


def update(table: str, filters: dict, patch: dict) -> list:
    params = {k: f"eq.{v}" for k, v in filters.items()}
    r = requests.patch(_url(table), headers=_headers({"Prefer": "return=representation"}),
                       params=params, json=patch, timeout=10)
    r.raise_for_status()
    return r.json()


def upsert(table: str, rows, on_conflict: str) -> list:
    if isinstance(rows, dict):
        rows = [rows]
    r = requests.post(_url(table),
                      headers=_headers({"Prefer": "resolution=merge-duplicates,return=representation"}),
                      params={"on_conflict": on_conflict}, json=rows, timeout=10)
    r.raise_for_status()
    return r.json()


def delete(table: str, filters: dict) -> None:
    params = {k: f"eq.{v}" for k, v in filters.items()}
    r = requests.delete(_url(table), headers=_headers(), params=params, timeout=10)
    r.raise_for_status()

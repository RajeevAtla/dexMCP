"""Targeted tests for dexmcp.api helper functions.

These tests cover cache behavior, error wrapping, and small utility helpers
that are otherwise difficult to exercise through higher-level calls.
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Dict, Optional

import pytest
import requests

import dexmcp.api as api


class DummyResponse:
    """Minimal response stub for requests.get."""

    def __init__(self, payload: Dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        """No-op for successful response."""

    def json(self) -> Dict[str, object]:
        """Return the payload."""
        return self._payload


def test_cached_fetch_and_fetch_json_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise cached fetch success and fetch_json error wrapping.

    Covers the happy path for HTTP requests and the error path in _fetch_json.
    """
    importlib.reload(api)
    api._cached_fetch.cache_clear()

    # Simulate a successful HTTP response without real network calls.
    def fake_get(url: str, timeout: int) -> DummyResponse:
        return DummyResponse({"ok": True})

    monkeypatch.setattr(api.requests, "get", fake_get)
    assert api._cached_fetch("https://example.test") == {"ok": True}

    # Simulate a request failure and ensure the error is wrapped.
    def raise_request_error(_: str) -> Dict[str, object]:
        raise requests.RequestException("boom")

    monkeypatch.setattr(api, "_cached_fetch", raise_request_error)
    with pytest.raises(ValueError, match="Failed to fetch context:"):
        api._fetch_json("https://example.test", context="context")


def test_list_all_types_filters_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Filter out ignored types from the canonical list.

    Ensures "shadow" (and other ignored types) are excluded.
    """
    api._list_all_types.cache_clear()

    # Feed a stubbed list with an ignored type.
    def fake_fetch_json(_: str, context: str) -> Dict[str, object]:
        return {"results": [{"name": "fire"}, {"name": "shadow"}, {"name": "water"}]}

    monkeypatch.setattr(api, "_fetch_json", fake_fetch_json)
    assert api._list_all_types() == ["fire", "water"]


def test_lookup_handles_digits_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Support numeric lookups and wrap lookup errors.

    Validates dex lookup, case-insensitive name lookup, and error wrapping.
    """
    stub = SimpleNamespace(name="stub")

    # Provide both dex and name resolution paths.
    def fake_get(*, name: Optional[str] = None, dex: Optional[int] = None):
        if dex == 25:
            return stub
        if name == "pikachu":
            return stub
        raise ValueError("not found")

    monkeypatch.setattr(api.pypokedex, "get", fake_get)
    assert api._lookup("25") is stub
    assert api._lookup("Pikachu") is stub
    # Unknown identifiers should raise a ValueError.
    with pytest.raises(ValueError, match="Could not find Pokemon"):
        api._lookup("missingno")


def test_extract_effect_helpers() -> None:
    """Extract English effect text or return None.

    Ensures both short and full effect helpers return English entries only.
    """
    short_entries = [{"language": {"name": "en"}, "short_effect": "Short text"}]
    effect_entries = [{"language": {"name": "en"}, "effect": "Long text"}]
    assert api._extract_short_effect(short_entries) == "Short text"
    assert api._extract_effect(effect_entries) == "Long text"

    # Non-English entries should be ignored.
    non_english = [{"language": {"name": "fr"}, "short_effect": "texte"}]
    assert api._extract_short_effect(non_english) is None
    assert api._extract_effect(non_english) is None

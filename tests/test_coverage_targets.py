"""Targeted tests to reach full coverage for edge cases."""

from __future__ import annotations

import importlib
import runpy
from types import SimpleNamespace
from typing import Dict, List, Optional

import pytest
import requests

import dexmcp.api as api
import dexmcp.coverage as coverage
import dexmcp.evolution as evolution
import dexmcp.moveset as moveset


class DummyResponse:
    """Minimal response stub for requests.get."""

    def __init__(self, payload: Dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        """No-op for successful response."""

    def json(self) -> Dict[str, object]:
        """Return the payload."""
        return self._payload


class DummyBaseStats:
    """Minimal base stat container for moveset tests."""

    def __init__(self, attack: int, sp_atk: int) -> None:
        self.attack = attack
        self.sp_atk = sp_atk


class DummyMove:
    """Minimal move entry for moveset tests."""

    def __init__(self, name: str, learn_method: str) -> None:
        self.name = name
        self.learn_method = learn_method
        self.level: Optional[int] = None


class DummyPokemon:
    """Minimal Pokemon container for moveset tests."""

    def __init__(self, name: str, types: List[str], moves: Dict[str, List[DummyMove]]) -> None:
        self.name = name
        self.types = types
        self.moves = moves
        self.base_stats = DummyBaseStats(attack=100, sp_atk=50)


def test_cached_fetch_and_fetch_json_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise cached fetch success and fetch_json error wrapping."""
    importlib.reload(api)
    api._cached_fetch.cache_clear()

    def fake_get(url: str, timeout: int) -> DummyResponse:
        return DummyResponse({"ok": True})

    monkeypatch.setattr(api.requests, "get", fake_get)
    assert api._cached_fetch("https://example.test") == {"ok": True}

    def raise_request_error(_: str) -> Dict[str, object]:
        raise requests.RequestException("boom")

    monkeypatch.setattr(api, "_cached_fetch", raise_request_error)
    with pytest.raises(ValueError, match="Failed to fetch context:"):
        api._fetch_json("https://example.test", context="context")


def test_list_all_types_filters_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Filter out ignored types from the canonical list."""
    api._list_all_types.cache_clear()

    def fake_fetch_json(_: str, context: str) -> Dict[str, object]:
        return {"results": [{"name": "fire"}, {"name": "shadow"}, {"name": "water"}]}

    monkeypatch.setattr(api, "_fetch_json", fake_fetch_json)
    assert api._list_all_types() == ["fire", "water"]


def test_lookup_handles_digits_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Support numeric lookups and wrap lookup errors."""
    stub = SimpleNamespace(name="stub")

    def fake_get(*, name: Optional[str] = None, dex: Optional[int] = None):
        if dex == 25:
            return stub
        if name == "pikachu":
            return stub
        raise ValueError("not found")

    monkeypatch.setattr(api.pypokedex, "get", fake_get)
    assert api._lookup("25") is stub
    assert api._lookup("Pikachu") is stub
    with pytest.raises(ValueError, match="Could not find Pokemon"):
        api._lookup("missingno")


def test_extract_effect_helpers() -> None:
    """Extract English effect text or return None."""
    short_entries = [{"language": {"name": "en"}, "short_effect": "Short text"}]
    effect_entries = [{"language": {"name": "en"}, "effect": "Long text"}]
    assert api._extract_short_effect(short_entries) == "Short text"
    assert api._extract_effect(effect_entries) == "Long text"

    non_english = [{"language": {"name": "fr"}, "short_effect": "texte"}]
    assert api._extract_short_effect(non_english) is None
    assert api._extract_effect(non_english) is None


def test_calc_multiplier_handles_unknown_and_immunity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return neutral for unknown types and zero for immunity."""

    def raise_unknown(_: str) -> Dict[str, List[str]]:
        raise ValueError("unknown type")

    monkeypatch.setattr(api, "_get_type_relations", raise_unknown)
    assert coverage._calc_multiplier("mystery", ["fire"]) == 1.0

    def immune_relations(_: str) -> Dict[str, List[str]]:
        return {"no_damage_to": ["ghost"], "double_damage_to": [], "half_damage_to": []}

    monkeypatch.setattr(api, "_get_type_relations", immune_relations)
    assert coverage._calc_multiplier("normal", ["ghost"]) == 0.0


def test_analyze_type_coverage_requires_roster() -> None:
    """Reject empty rosters for coverage analysis."""
    with pytest.raises(ValueError, match="names_or_dexes must contain at least one Pokemon"):
        coverage.analyze_type_coverage([])


def test_gender_from_rate_handles_genderless() -> None:
    """Convert genderless rate to zeroed percentages."""
    gender = importlib.import_module("dexmcp.breeding")._gender_from_rate(-1)
    assert gender.female_percent == 0.0
    assert gender.male_percent == 0.0


def test_evolution_conditions_and_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Capture evolution conditions and fallback when no direct path."""
    chain = {
        "species": {"name": "root"},
        "evolves_to": [
            {
                "species": {"name": "next"},
                "evolution_details": [
                    {
                        "trigger": {"name": "level-up"},
                        "min_level": 16,
                        "time_of_day": "night",
                        "known_move_type": {"name": "dark"},
                        "needs_overworld_rain": True,
                        "extra": None,
                    }
                ],
                "evolves_to": [],
            }
        ],
    }
    paths: List[evolution.EvolutionPath] = []
    evolution._expand_chain(chain, [], paths)
    assert paths
    conditions = paths[0].steps[0].conditions
    assert conditions == {
        "time_of_day": "night",
        "known_move_type": "dark",
        "needs_overworld_rain": "True",
    }

    dummy_pk = SimpleNamespace(name="missingmon", dex=999)

    def fake_lookup(_: str):
        return dummy_pk

    def fake_fetch_json(url: str, context: str) -> Dict[str, object]:
        if "pokemon-species" in url:
            return {"evolution_chain": {"url": "https://example.test/chain/1"}}
        return {"chain": chain}

    monkeypatch.setattr(api, "_lookup", fake_lookup)
    monkeypatch.setattr(api, "_fetch_json", fake_fetch_json)
    report = evolution.plan_evolutions("missingmon")
    assert report.paths


def test_plan_evolutions_handles_missing_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return empty paths when no evolution chain URL is present."""
    dummy_pk = SimpleNamespace(name="solo", dex=1)

    def fake_lookup(_: str):
        return dummy_pk

    def fake_fetch_json(_: str, context: str) -> Dict[str, object]:
        return {}

    monkeypatch.setattr(api, "_lookup", fake_lookup)
    monkeypatch.setattr(api, "_fetch_json", fake_fetch_json)
    report = evolution.plan_evolutions("solo")
    assert report.paths == []


def test_moveset_filters_and_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise filtering and default scoring paths in moveset."""
    dummy_moves = [
        DummyMove("egg-move", "egg"),
        DummyMove("tm-move", "machine"),
        DummyMove("status-move", "level-up"),
        DummyMove("bad-move", "level-up"),
        DummyMove("powerless-move", "level-up"),
    ]
    dummy_pk = DummyPokemon("stubmon", ["normal"], {"demo-game": dummy_moves})

    def fake_lookup(_: str):
        return dummy_pk

    def fake_move_data(name: str) -> Dict[str, object]:
        if name == "bad-move":
            raise ValueError("missing move")
        if name == "status-move":
            return {"damage_class": {"name": "status"}, "power": None, "accuracy": None, "type": {"name": "normal"}}
        if name == "egg-move":
            return {"damage_class": {"name": "physical"}, "power": 40, "accuracy": 100, "type": {"name": "normal"}}
        return {"damage_class": {"name": "physical"}, "power": None, "accuracy": None, "type": {"name": "normal"}}

    monkeypatch.setattr(api, "_lookup", fake_lookup)
    monkeypatch.setattr(api, "_get_move_data", fake_move_data)

    result = moveset.suggest_moveset("stubmon", game="demo-game", include_tm=False)
    assert [move.name for move in result.recommendations] == ["powerless-move"]


def test_server_main_invokes_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invoke the __main__ path without starting a real server."""
    called = {"run": False}

    def fake_run(self) -> None:
        called["run"] = True

    monkeypatch.setattr("mcp.server.fastmcp.FastMCP.run", fake_run)
    runpy.run_module("dexmcp.server", run_name="__main__")
    assert called["run"]

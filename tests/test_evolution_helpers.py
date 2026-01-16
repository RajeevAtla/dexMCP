"""Targeted tests for dexmcp.evolution helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, List

import pytest

import dexmcp.api as api
import dexmcp.evolution as evolution


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

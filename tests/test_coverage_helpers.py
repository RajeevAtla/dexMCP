"""Targeted tests for dexmcp.coverage helpers."""

from __future__ import annotations

from typing import Dict, List

import pytest

import dexmcp.api as api
import dexmcp.coverage as coverage


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

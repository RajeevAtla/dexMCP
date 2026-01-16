"""Targeted tests for dexmcp.coverage helpers.

These unit tests focus on calculation edge cases and validation behavior.
"""

from __future__ import annotations

from typing import Dict, List

import pytest

import dexmcp.api as api
import dexmcp.coverage as coverage


def test_calc_multiplier_handles_unknown_and_immunity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return neutral for unknown types and zero for immunity.

    Verifies both the error path in _get_type_relations and no-damage matches.
    """

    # Force an error so the function returns a neutral multiplier.
    def raise_unknown(_: str) -> Dict[str, List[str]]:
        raise ValueError("unknown type")

    monkeypatch.setattr(api, "_get_type_relations", raise_unknown)
    assert coverage._calc_multiplier("mystery", ["fire"]) == 1.0

    # Return a no-damage relationship to force an immunity result.
    def immune_relations(_: str) -> Dict[str, List[str]]:
        return {"no_damage_to": ["ghost"], "double_damage_to": [], "half_damage_to": []}

    monkeypatch.setattr(api, "_get_type_relations", immune_relations)
    assert coverage._calc_multiplier("normal", ["ghost"]) == 0.0


def test_analyze_type_coverage_requires_roster() -> None:
    """Reject empty rosters for coverage analysis.

    Empty input should raise a ValueError with a clear message.
    """
    # The roster list is required for meaningful coverage output.
    with pytest.raises(ValueError, match="names_or_dexes must contain at least one Pokemon"):
        coverage.analyze_type_coverage([])

"""Targeted tests for dexmcp.moveset helpers."""

from __future__ import annotations

from typing import Dict, List, Optional

import pytest

import dexmcp.api as api
import dexmcp.moveset as moveset


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

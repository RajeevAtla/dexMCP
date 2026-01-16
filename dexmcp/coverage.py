"""Defensive type coverage analysis helpers."""

from __future__ import annotations

from typing import List, Sequence

from . import api
from .models import TypeCoverageReport, TypeMatchupSummary


def _calc_multiplier(attack_type: str, defend_types: Sequence[str]) -> float:
    """Return damage multiplier for an attack type against defensive types.

    Args:
        attack_type: Attacking type name.
        defend_types: Defending type names for the Pokemon.

    Returns:
        Damage multiplier for the matchup.
    """
    # Each attacking type maps to a damage relation table.
    try:
        relations = api._get_type_relations(attack_type)
    except ValueError:
        # Unknown types are treated as neutral.
        return 1.0

    # Multiply type modifiers for dual-typed Pokemon.
    multiplier = 1.0
    for defend_type in defend_types:
        if defend_type in relations.get("no_damage_to", []):
            return 0.0
        if defend_type in relations.get("double_damage_to", []):
            multiplier *= 2.0
        elif defend_type in relations.get("half_damage_to", []):
            multiplier *= 0.5
    return multiplier


def analyze_type_coverage(names_or_dexes: List[str]) -> TypeCoverageReport:
    """Summarize defensive coverage for a roster of Pokemon.

    Args:
        names_or_dexes: Pokemon names or dex numbers to analyze.

    Returns:
        Coverage report with matchup counts and notable strengths/weaknesses.

    Raises:
        ValueError: If no Pokemon identifiers are provided.
    """
    # Helps team builders quickly spot shared weaknesses before heading into a battle.
    # Defensive coverage requires at least one Pokemon.
    if not names_or_dexes:
        raise ValueError("names_or_dexes must contain at least one Pokemon")

    # Resolve the roster once to avoid repeated lookups.
    team_pokemon = [api._lookup(identifier) for identifier in names_or_dexes]
    matchup_rows: List[TypeMatchupSummary] = []

    # Evaluate every attacking type against each team member.
    for attack_type in api._list_all_types():
        weak = resistant = immune = neutral = 0
        for pk in team_pokemon:
            multiplier = _calc_multiplier(attack_type, pk.types)
            if multiplier == 0:
                immune += 1
            elif multiplier > 1:
                weak += 1
            elif multiplier < 1:
                resistant += 1
            else:
                neutral += 1
        matchup_rows.append(
            TypeMatchupSummary(
                attack_type=attack_type,
                weak=weak,
                resistant=resistant,
                immune=immune,
                neutral=neutral,
            )
        )

    # Compute summary highlights for quick scanning.
    roster_size = len(team_pokemon)
    notable_weak = [
        row.attack_type
        for row in matchup_rows
        if row.weak >= max(1, (roster_size + 1) // 2)
    ]
    notable_resist = [
        row.attack_type
        for row in matchup_rows
        if row.resistant + row.immune == roster_size
    ]
    # Return a single report with roster names and matchup summaries.
    return TypeCoverageReport(
        team=[pk.name for pk in team_pokemon],
        matchup_summary=matchup_rows,
        notable_weaknesses=notable_weak,
        notable_resistances=notable_resist,
    )

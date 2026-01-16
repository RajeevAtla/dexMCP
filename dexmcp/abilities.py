"""Ability lookup helpers."""

from __future__ import annotations

from typing import List

from . import api
from .models import AbilityDetail, AbilityExplorerResult


def explore_abilities(name_or_dex: str) -> AbilityExplorerResult:
    """Return detailed ability information with effect text.

    Args:
        name_or_dex: Pokemon name or national dex number.

    Returns:
        Ability details including hidden ability flags and effect text.
    """
    # Fetch each ability's effect text directly from PokeAPI so clients do not need a second integration.
    pk = api._lookup(name_or_dex)
    abilities: List[AbilityDetail] = []
    for ability in pk.abilities:
        # Each ability needs its own endpoint call to fetch effect text.
        data = api._fetch_json(
            f"https://pokeapi.co/api/v2/ability/{ability.name}",
            context=f"ability data for {ability.name}",
        )
        effect_entries = data.get("effect_entries", [])
        # Convert raw API data into the model the MCP tool returns.
        abilities.append(
            AbilityDetail(
                name=ability.name,
                is_hidden=ability.is_hidden,
                short_effect=api._extract_short_effect(effect_entries),
                effect=api._extract_effect(effect_entries),
            )
        )
    return AbilityExplorerResult(pokemon=pk.name, abilities=abilities)

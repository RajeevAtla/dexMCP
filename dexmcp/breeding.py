"""Breeding-related helpers for egg groups and moves."""

from __future__ import annotations

from typing import List, Optional

from . import api
from .models import BreedingInfo, GenderRatio


def _gender_from_rate(gender_rate: int) -> GenderRatio:
    """Convert the PokeAPI gender rate into percentages.

    Args:
        gender_rate: PokeAPI gender rate (-1 for genderless, 0-8 otherwise).

    Returns:
        Female and male percentages for the species.
    """
    if gender_rate == -1:
        return GenderRatio(female_percent=0.0, male_percent=0.0)
    female = (gender_rate / 8.0) * 100.0
    male = 100.0 - female
    return GenderRatio(female_percent=round(female, 2), male_percent=round(male, 2))


def get_breeding_info(name_or_dex: str, game: Optional[str] = None) -> BreedingInfo:
    """Summarize egg groups, hatch steps, gender ratio, and egg moves.

    Args:
        name_or_dex: Pokemon name or national dex number.
        game: Optional game identifier to filter egg moves.

    Returns:
        Breeding metadata for the Pokemon.
    """
    # Combines species metadata with move learnsets so breeders see everything in one response.
    pk = api._lookup(name_or_dex)
    species_data = api._fetch_json(
        f"https://pokeapi.co/api/v2/pokemon-species/{pk.dex}",
        context=f"species data for {pk.name}",
    )
    egg_groups = [group["name"] for group in species_data.get("egg_groups", [])]
    hatch_counter = species_data.get("hatch_counter")
    hatch_steps = (hatch_counter + 1) * 255 if hatch_counter is not None else None
    gender = _gender_from_rate(species_data.get("gender_rate", -1))

    egg_moves: List[str] = []
    if game:
        moves = pk.moves.get(game, [])
        egg_moves = sorted({move.name for move in moves if move.learn_method == "egg"})
    else:
        for moves in pk.moves.values():
            for move in moves:
                if move.learn_method == "egg":
                    egg_moves.append(move.name)
        egg_moves = sorted(set(egg_moves))

    return BreedingInfo(
        pokemon=pk.name,
        egg_groups=egg_groups,
        gender=gender,
        hatch_steps=hatch_steps,
        egg_moves=egg_moves,
    )

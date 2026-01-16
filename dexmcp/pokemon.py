"""Pokemon lookup helpers used by MCP tool wrappers."""

from __future__ import annotations

from typing import Dict, List, Optional

from . import api
from .models import BaseStats, Move, PokemonSummary, SpriteURL


def get_pokemon(name_or_dex: str) -> PokemonSummary:
    """Look up a Pokemon and return summary stats.

    Args:
        name_or_dex: Pokemon name (e.g., "garchomp") or dex number (e.g., "445").

    Returns:
        Summary stats, typing, measurements, and base experience.
    """
    pk = api._lookup(name_or_dex)

    # pk.base_stats is a namedtuple; convert to our model
    stats = BaseStats(
        hp=pk.base_stats.hp,
        attack=pk.base_stats.attack,
        defense=pk.base_stats.defense,
        sp_atk=pk.base_stats.sp_atk,
        sp_def=pk.base_stats.sp_def,
        speed=pk.base_stats.speed,
    )

    # Height and weight keep both raw and derived units so clients can choose the display they prefer.
    return PokemonSummary(
        dex=pk.dex,
        name=pk.name,
        types=list(pk.types),
        height_dm=pk.height,  # decimeters per pypokedex/PokeAPI
        height_m=pk.height / 10.0,  # convert dm -> m
        weight_hg=pk.weight,  # hectograms per pypokedex/PokeAPI
        weight_kg=pk.weight / 10.0,  # convert hg -> kg
        base_experience=pk.base_experience,
        base_stats=stats,
    )


def get_moves(name_or_dex: str, game: str) -> List[Move]:
    """List the moves a Pokemon can learn in a given game.

    Args:
        name_or_dex: Pokemon name or national dex number.
        game: PokeAPI game identifier (e.g., "scarlet-violet").

    Returns:
        Moves learnable in the requested game.
    """
    pk = api._lookup(name_or_dex)
    # pypokedex exposes move data keyed by game identifier (e.g., 'scarlet-violet'). Missing keys return [].
    moves_for_game = pk.moves.get(game, [])
    return [Move(name=m.name, learn_method=m.learn_method, level=m.level) for m in moves_for_game]


def get_sprites(name_or_dex: str, side: str = "front", variant: str = "default") -> SpriteURL:
    """Return a direct URL to a Pokemon sprite.

    Args:
        name_or_dex: Pokemon name or national dex number.
        side: Sprite side ("front" or "back").
        variant: Sprite variant (e.g., "default", "shiny", "female").

    Returns:
        Sprite URL metadata for the requested variant.

    Raises:
        ValueError: If the sprite side is not "front" or "back".
    """
    if side not in {"front", "back"}:
        # Validate inputs early so downstream tooling gets actionable errors.
        raise ValueError("side must be 'front' or 'back'")
    pk = api._lookup(name_or_dex)

    # pk.sprites.{front,back} are dicts with keys like 'default','shiny','female','female_shiny'
    sprite_dict: Dict[str, Optional[str]] = getattr(pk.sprites, side)
    url = sprite_dict.get(variant)
    return SpriteURL(url=url, side=side, variant=variant)


def get_descriptions(name_or_dex: str, language: str = "en") -> Dict[str, str]:
    """Return flavor text descriptions in the requested language.

    Args:
        name_or_dex: Pokemon name or national dex number.
        language: Language code for the flavor text.

    Returns:
        Mapping of game version to flavor text.
    """
    pk = api._lookup(name_or_dex)
    # Flavor text comes from multiple game entries; keep the raw mapping so clients can pick the ones they need.
    return pk.get_descriptions(language=language)

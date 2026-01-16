"""Moveset recommendation logic and heuristics."""

from __future__ import annotations

from typing import List

from . import api
from .models import MoveRecommendation, MovesetRecommendation


# Lightweight heuristic that ranks damaging moves by power, accuracy, STAB, and stat alignment.
def suggest_moveset(
    name_or_dex: str,
    game: str,
    limit: int = 4,
    include_tm: bool = False,
) -> MovesetRecommendation:
    """Recommend high-impact moves using a simple heuristic.

    Args:
        name_or_dex: Pokemon name or national dex number.
        game: PokeAPI game identifier to scope the learnset.
        limit: Maximum number of moves to return.
        include_tm: Whether to include TM moves in the candidate pool.

    Returns:
        Ranked moveset recommendations for the Pokemon.

    Raises:
        ValueError: If the game has no move data for the Pokemon.
    """
    # Resolve the Pokemon and the learnset for the requested game.
    pk = api._lookup(name_or_dex)
    moves = pk.moves.get(game)
    if moves is None:
        raise ValueError(f"No move data for game '{game}'")

    # Decide whether to favor physical or special moves based on base stats.
    preferred_class = "physical" if pk.base_stats.attack >= pk.base_stats.sp_atk else "special"
    # Collect candidate moves before ranking.
    candidates: List[MoveRecommendation] = []
    for move in moves:
        # Skip egg moves; breeding helper surfaces those separately.
        if move.learn_method == "egg":
            continue  # egg moves are covered by the breeding helper
        # Respect user preference for TM inclusion.
        if not include_tm and move.learn_method not in {"level-up", "tutor"}:
            continue
        try:
            move_data = api._get_move_data(move.name)
        except ValueError:
            # If the move can't be fetched, drop it from consideration.
            continue

        # Only score damaging moves; status moves get filtered out here.
        damage_class = (move_data.get("damage_class") or {}).get("name")
        if damage_class not in {"physical", "special"}:
            continue

        # Pull the components needed for scoring.
        power = move_data.get("power")
        accuracy = move_data.get("accuracy")
        move_type = (move_data.get("type") or {}).get("name")
        # Same-type attack bonus (STAB) increases the score.
        stab = move_type in pk.types if move_type else False
        # Use a default accuracy factor when accuracy is missing.
        accuracy_factor = (accuracy / 100.0) if accuracy else 0.85
        # Power defaults to 0 when missing.
        power_factor = power or 0
        # Bias toward the Pokemon's stronger attack class.
        class_factor = 1.1 if damage_class == preferred_class else 0.9
        # Reward STAB slightly.
        stab_factor = 1.3 if stab else 1.0
        # Final heuristic score.
        score = power_factor * accuracy_factor * class_factor * stab_factor
        # Pull effect text for richer output.
        effect_entries = move_data.get("effect_entries", [])
        recommendation = MoveRecommendation(
            name=move.name,
            move_type=move_type,
            power=power,
            accuracy=accuracy,
            damage_class=damage_class,
            learn_method=move.learn_method,
            level=move.level,
            stab=stab,
            score=round(score, 2),
            short_effect=api._extract_short_effect(effect_entries),
            effect=api._extract_effect(effect_entries),
        )
        candidates.append(recommendation)

    # Highest scoring moves first.
    candidates.sort(key=lambda rec: rec.score, reverse=True)
    return MovesetRecommendation(
        pokemon=pk.name,
        game=game,
        recommendations=candidates[:limit],
    )

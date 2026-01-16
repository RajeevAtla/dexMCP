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
    """Recommend high-impact moves for a Pokemon in a given game using simple heuristics."""
    pk = api._lookup(name_or_dex)
    moves = pk.moves.get(game)
    if moves is None:
        raise ValueError(f"No move data for game '{game}'")

    preferred_class = "physical" if pk.base_stats.attack >= pk.base_stats.sp_atk else "special"
    candidates: List[MoveRecommendation] = []
    for move in moves:
        if move.learn_method == "egg":
            continue  # egg moves are covered by the breeding helper
        if not include_tm and move.learn_method not in {"level-up", "tutor"}:
            continue
        try:
            move_data = api._get_move_data(move.name)
        except ValueError:
            continue

        damage_class = (move_data.get("damage_class") or {}).get("name")
        if damage_class not in {"physical", "special"}:
            continue

        power = move_data.get("power")
        accuracy = move_data.get("accuracy")
        move_type = (move_data.get("type") or {}).get("name")
        stab = move_type in pk.types if move_type else False
        accuracy_factor = (accuracy / 100.0) if accuracy else 0.85
        power_factor = power or 0
        class_factor = 1.1 if damage_class == preferred_class else 0.9
        stab_factor = 1.3 if stab else 1.0
        score = power_factor * accuracy_factor * class_factor * stab_factor
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

    candidates.sort(key=lambda rec: rec.score, reverse=True)
    return MovesetRecommendation(
        pokemon=pk.name,
        game=game,
        recommendations=candidates[:limit],
    )

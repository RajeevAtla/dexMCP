import math

import pytest

import dexmcp.dexmcp_server as server


def test_get_pokemon_returns_expected_summary() -> None:
    summary = server.get_pokemon("garchomp")
    assert summary.dex == 445
    assert summary.name == "garchomp"
    assert summary.types == ["dragon", "ground"]
    assert math.isclose(summary.height_m, 1.9)
    assert summary.base_stats.attack == 130


def test_get_moves_returns_filtered_learnset() -> None:
    moves = server.get_moves("garchomp", game="omega-ruby-alpha-sapphire")
    names = {move.name for move in moves}
    assert {"dragon-claw", "earthquake", "stone-edge", "swords-dance"} == names


def test_get_moves_handles_missing_game() -> None:
    moves = server.get_moves("garchomp", game="non-existent")
    assert moves == []


def test_get_sprites_validates_side() -> None:
    with pytest.raises(ValueError):
        server.get_sprites("garchomp", side="left")


def test_get_sprites_returns_variant_url() -> None:
    sprite = server.get_sprites("garchomp", variant="shiny")
    assert sprite.url.endswith("front-shiny.png")


def test_get_descriptions_respects_language() -> None:
    descriptions = server.get_descriptions("garchomp")
    assert "omega-ruby" in descriptions


def test_analyze_type_coverage_flags_ice_weakness() -> None:
    report = server.analyze_type_coverage(["garchomp", "pikachu", "gyarados"])
    matchup = next(entry for entry in report.matchup_summary if entry.attack_type == "ice")
    assert matchup.weak >= 1
    assert matchup.resistant + matchup.immune < len(report.team)


def test_explore_abilities_returns_effect_text() -> None:
    abilities = server.explore_abilities("garchomp")
    sand_veil = next(entry for entry in abilities.abilities if entry.name == "sand-veil")
    assert sand_veil.short_effect.startswith("Raises evasion")
    assert sand_veil.is_hidden is False


def test_plan_evolutions_lists_full_chain() -> None:
    report = server.plan_evolutions("garchomp")
    assert report.paths, "Expected at least one evolution path"
    steps = report.paths[0].steps
    assert steps[0].from_species == "gible"
    assert steps[-1].to_species == "garchomp"


def test_find_encounters_groups_by_location() -> None:
    report = server.find_encounters("garchomp")
    assert report.locations[0].location_area == "victory-road"
    version = report.locations[0].versions[0]
    assert version.version == "omega-ruby"
    assert version.details[0].method == "walk"


def test_get_breeding_info_filters_egg_moves_by_game() -> None:
    info = server.get_breeding_info("garchomp", game="sun-moon")
    assert info.egg_groups == ["monster", "dragon"]
    assert info.egg_moves == ["hydro-pump", "iron-tail"]
    assert info.hatch_steps == (40 + 1) * 255


def test_get_breeding_info_deduplicates_all_egg_moves() -> None:
    info = server.get_breeding_info("garchomp")
    assert info.egg_moves == ["hydro-pump", "iron-tail"]


def test_suggest_moveset_prioritises_stab_and_physical() -> None:
    recommendation = server.suggest_moveset("garchomp", game="omega-ruby-alpha-sapphire", limit=3)
    move_names = [move.name for move in recommendation.recommendations]
    assert move_names[0] == "earthquake"
    assert "swords-dance" not in move_names


def test_suggest_moveset_errors_for_unknown_game() -> None:
    with pytest.raises(ValueError):
        server.suggest_moveset("garchomp", game="unknown")

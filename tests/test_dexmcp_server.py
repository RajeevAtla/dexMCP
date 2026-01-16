"""Tests for DexMCP server tool wrappers.

These tests validate that the MCP tool wrappers return the expected payloads
and handle edge cases cleanly when data is missing or invalid inputs are used.
"""

import math

import pytest

import dexmcp.server as server


def test_get_pokemon_returns_expected_summary() -> None:
    """Ensure Pokemon summary fields are populated.

    Verifies core identifiers, typing, and a representative base stat field.
    """
    # Act
    summary = server.get_pokemon("garchomp")
    # Assert
    assert summary.dex == 445
    assert summary.name == "garchomp"
    assert summary.types == ["dragon", "ground"]
    assert math.isclose(summary.height_m, 1.9)
    assert summary.base_stats.attack == 130


def test_get_moves_returns_filtered_learnset() -> None:
    """Verify move filtering by game identifier.

    Ensures the wrapper reads the correct per-game learnset.
    """
    # Act
    moves = server.get_moves("garchomp", game="omega-ruby-alpha-sapphire")
    # Assert
    names = {move.name for move in moves}
    assert {"dragon-claw", "earthquake", "stone-edge", "swords-dance"} == names


def test_get_moves_handles_missing_game() -> None:
    """Return an empty list when move data is missing.

    Missing keys should degrade gracefully rather than raising.
    """
    # Act
    moves = server.get_moves("garchomp", game="non-existent")
    # Assert
    assert moves == []


def test_get_sprites_validates_side() -> None:
    """Validate sprite side inputs.

    Ensures invalid sides raise a clear ValueError.
    """
    # Act/Assert
    with pytest.raises(ValueError):
        server.get_sprites("garchomp", side="left")


def test_get_sprites_returns_variant_url() -> None:
    """Resolve sprite URLs for variants.

    Confirms the URL includes the variant name for shiny sprites.
    """
    # Act
    sprite = server.get_sprites("garchomp", variant="shiny")
    # Assert
    assert sprite.url.endswith("front-shiny.png")


def test_get_descriptions_respects_language() -> None:
    """Return flavor text entries for the default language.

    The stubbed descriptions should include a known game entry.
    """
    # Act
    descriptions = server.get_descriptions("garchomp")
    # Assert
    assert "omega-ruby" in descriptions


def test_analyze_type_coverage_flags_ice_weakness() -> None:
    """Highlight notable weaknesses in a coverage report.

    Ice should threaten a roster with Garchomp, Pikachu, and Gyarados.
    """
    # Act
    report = server.analyze_type_coverage(["garchomp", "pikachu", "gyarados"])
    # Assert
    matchup = next(entry for entry in report.matchup_summary if entry.attack_type == "ice")
    assert matchup.weak >= 1
    assert matchup.resistant + matchup.immune < len(report.team)


def test_explore_abilities_returns_effect_text() -> None:
    """Return ability effect text for Pokemon abilities.

    Validates that effect text is included and hidden ability flags are present.
    """
    # Act
    abilities = server.explore_abilities("garchomp")
    # Assert
    sand_veil = next(entry for entry in abilities.abilities if entry.name == "sand-veil")
    assert sand_veil.short_effect.startswith("Raises evasion")
    assert sand_veil.is_hidden is False


def test_plan_evolutions_lists_full_chain() -> None:
    """Return at least one evolution path in the chain.

    Ensures evolution paths start and end with expected species.
    """
    # Act
    report = server.plan_evolutions("garchomp")
    # Assert
    assert report.paths, "Expected at least one evolution path"
    steps = report.paths[0].steps
    assert steps[0].from_species == "gible"
    assert steps[-1].to_species == "garchomp"


def test_find_encounters_groups_by_location() -> None:
    """Group encounter details by location and version.

    Confirms the first location entry matches the stubbed data.
    """
    # Act
    report = server.find_encounters("garchomp")
    # Assert
    assert report.locations[0].location_area == "victory-road"
    version = report.locations[0].versions[0]
    assert version.version == "omega-ruby"
    assert version.details[0].method == "walk"


def test_get_breeding_info_filters_egg_moves_by_game() -> None:
    """Filter egg moves by game when requested.

    Validates that the filtered egg move list matches the stubbed learnset.
    """
    # Act
    info = server.get_breeding_info("garchomp", game="sun-moon")
    # Assert
    assert info.egg_groups == ["monster", "dragon"]
    assert info.egg_moves == ["hydro-pump", "iron-tail"]
    assert info.hatch_steps == (40 + 1) * 255


def test_get_breeding_info_deduplicates_all_egg_moves() -> None:
    """Deduplicate egg moves across games.

    Ensures egg moves collected across games are unique and sorted.
    """
    # Act
    info = server.get_breeding_info("garchomp")
    # Assert
    assert info.egg_moves == ["hydro-pump", "iron-tail"]


def test_suggest_moveset_prioritises_stab_and_physical() -> None:
    """Prefer STAB physical moves when appropriate.

    Confirms that the top move is a strong physical STAB option.
    """
    # Act
    recommendation = server.suggest_moveset("garchomp", game="omega-ruby-alpha-sapphire", limit=3)
    # Assert
    move_names = [move.name for move in recommendation.recommendations]
    assert move_names[0] == "earthquake"
    assert "swords-dance" not in move_names


def test_suggest_moveset_errors_for_unknown_game() -> None:
    """Raise a ValueError when move data is missing.

    Unknown games should surface an explicit error rather than empty output.
    """
    # Act/Assert
    with pytest.raises(ValueError):
        server.suggest_moveset("garchomp", game="unknown")

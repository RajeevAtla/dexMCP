from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional

import pytest

import dexmcp.api as api


@dataclass
class StubBaseStats:
    hp: int
    attack: int
    defense: int
    sp_atk: int
    sp_def: int
    speed: int


class StubMove:
    def __init__(self, name: str, learn_method: str, level: Optional[int] = None) -> None:
        self.name = name
        self.learn_method = learn_method
        self.level = level


class StubSprites:
    def __init__(self, front: Dict[str, Optional[str]], back: Dict[str, Optional[str]]) -> None:
        self.front = front
        self.back = back


class StubPokemon:
    def __init__(
        self,
        name: str,
        dex: int,
        types: Iterable[str],
        base_stats: StubBaseStats,
        moves: Dict[str, List[StubMove]],
        abilities: Iterable[SimpleNamespace],
        descriptions: Dict[str, Dict[str, str]],
        height_dm: int = 19,
        weight_hg: int = 950,
        base_experience: int = 270,
    ) -> None:
        self.name = name
        self.dex = dex
        self.types = tuple(types)
        self.base_stats = base_stats
        self.moves = moves
        self.abilities = list(abilities)
        self._descriptions = descriptions
        self.height = height_dm
        self.weight = weight_hg
        self.base_experience = base_experience
        self.sprites = StubSprites(
            front={
                "default": f"https://img.poke/{name}/front.png",
                "shiny": f"https://img.poke/{name}/front-shiny.png",
            },
            back={
                "default": f"https://img.poke/{name}/back.png",
                "shiny": f"https://img.poke/{name}/back-shiny.png",
            },
        )

    def get_descriptions(self, language: str = "en") -> Dict[str, str]:
        return self._descriptions.get(language, {})


@pytest.fixture(autouse=True)
def reset_caches() -> None:
    api._cached_fetch.cache_clear()
    api._list_all_types.cache_clear()
    api._get_type_relations.cache_clear()
    api._get_move_data.cache_clear()


@pytest.fixture(autouse=True)
def stubbed_external_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    base_stats = StubBaseStats(hp=108, attack=130, defense=95, sp_atk=80, sp_def=85, speed=102)
    garchomp_moves = {
        "omega-ruby-alpha-sapphire": [
            StubMove("dragon-claw", "level-up", level=24),
            StubMove("earthquake", "level-up", level=48),
            StubMove("stone-edge", "tutor", None),
            StubMove("swords-dance", "level-up", level=36),
        ],
        "sun-moon": [
            StubMove("iron-tail", "egg", None),
            StubMove("hydro-pump", "egg", None),
        ],
    }
    descriptions = {
        "en": {
            "omega-ruby": "It flies at sonic speed, taking on its foes head-on.",
        }
    }
    garchomp = StubPokemon(
        name="garchomp",
        dex=445,
        types=["dragon", "ground"],
        base_stats=base_stats,
        moves=garchomp_moves,
        abilities=[
            SimpleNamespace(name="sand-veil", is_hidden=False),
            SimpleNamespace(name="rough-skin", is_hidden=True),
        ],
        descriptions=descriptions,
        height_dm=19,
        weight_hg=950,
        base_experience=270,
    )

    pikachu_stats = StubBaseStats(hp=35, attack=55, defense=40, sp_atk=50, sp_def=50, speed=90)
    pikachu = StubPokemon(
        name="pikachu",
        dex=25,
        types=["electric"],
        base_stats=pikachu_stats,
        moves={"scarlet-violet": [StubMove("thunderbolt", "level-up", level=36)]},
        abilities=[SimpleNamespace(name="static", is_hidden=False)],
        descriptions={"en": {"scarlet": "It stores electricity in its cheeks."}},
        height_dm=4,
        weight_hg=60,
        base_experience=112,
    )

    gyarados_stats = StubBaseStats(hp=95, attack=125, defense=79, sp_atk=60, sp_def=100, speed=81)
    gyarados = StubPokemon(
        name="gyarados",
        dex=130,
        types=["water", "flying"],
        base_stats=gyarados_stats,
        moves={"scarlet-violet": [StubMove("hurricane", "tutor", None)]},
        abilities=[SimpleNamespace(name="intimidate", is_hidden=False)],
        descriptions={"en": {"violet": "Once it begins to rage, it cannot stop."}},
        height_dm=65,
        weight_hg=2350,
        base_experience=189,
    )

    pokemon_registry = {
        "garchomp": garchomp,
        "pikachu": pikachu,
        "gyarados": gyarados,
        445: garchomp,
        25: pikachu,
        130: gyarados,
    }

    def fake_get(*, name: Optional[str] = None, dex: Optional[int] = None):
        if name is not None:
            key = name.lower()
            if key in pokemon_registry:
                return pokemon_registry[key]
        if dex is not None and dex in pokemon_registry:
            return pokemon_registry[dex]
        raise ValueError("Pokemon not found")

    monkeypatch.setattr(api.pypokedex, "get", fake_get)

    type_list = ["dragon", "ground", "electric", "water", "flying", "ice"]

    type_relations = {
        "dragon": {
            "double_damage_to": [{"name": "dragon"}],
            "half_damage_to": [{"name": "steel"}],
            "no_damage_to": [],
        },
        "ground": {
            "double_damage_to": [{"name": "electric"}, {"name": "fire"}],
            "half_damage_to": [{"name": "grass"}],
            "no_damage_to": [{"name": "flying"}],
        },
        "electric": {
            "double_damage_to": [{"name": "water"}, {"name": "flying"}],
            "half_damage_to": [{"name": "grass"}],
            "no_damage_to": [{"name": "ground"}],
        },
        "water": {
            "double_damage_to": [{"name": "fire"}],
            "half_damage_to": [{"name": "water"}],
            "no_damage_to": [],
        },
        "flying": {
            "double_damage_to": [{"name": "grass"}],
            "half_damage_to": [{"name": "electric"}],
            "no_damage_to": [],
        },
        "ice": {
            "double_damage_to": [{"name": "dragon"}, {"name": "ground"}, {"name": "flying"}],
            "half_damage_to": [{"name": "fire"}, {"name": "water"}],
            "no_damage_to": [],
        },
    }

    ability_entries = {
        "sand-veil": {
            "effect_entries": [
                {"language": {"name": "en"}, "short_effect": "Raises evasion in a sandstorm.", "effect": "Boosts evasion by 20% in a sandstorm."}
            ]
        },
        "rough-skin": {
            "effect_entries": [
                {"language": {"name": "en"}, "short_effect": "Damages attackers on contact.", "effect": "Inflicts damage to the attacker on contact."}
            ]
        },
        "static": {
            "effect_entries": [
                {"language": {"name": "en"}, "short_effect": "May paralyze on contact.", "effect": "Has a chance to paralyze attackers."}
            ]
        },
        "intimidate": {
            "effect_entries": [
                {"language": {"name": "en"}, "short_effect": "Lowers the foe's Attack stat.", "effect": "Lowers the opposing Pokemon's Attack."}
            ]
        },
    }

    move_entries = {
        "dragon-claw": {
            "damage_class": {"name": "physical"},
            "power": 80,
            "accuracy": 100,
            "type": {"name": "dragon"},
            "effect_entries": [
                {"language": {"name": "en"}, "short_effect": "Slashes with sharp claws.", "effect": "Inflicts regular damage."}
            ],
        },
        "earthquake": {
            "damage_class": {"name": "physical"},
            "power": 100,
            "accuracy": 100,
            "type": {"name": "ground"},
            "effect_entries": [
                {"language": {"name": "en"}, "short_effect": "Hits all Pokemon on the ground.", "effect": "Powerful ground-type attack."}
            ],
        },
        "stone-edge": {
            "damage_class": {"name": "physical"},
            "power": 100,
            "accuracy": 80,
            "type": {"name": "rock"},
            "effect_entries": [
                {"language": {"name": "en"}, "short_effect": "High critical-hit ratio.", "effect": "May result in a critical hit."}
            ],
        },
        "swords-dance": {
            "damage_class": {"name": "status"},
            "power": None,
            "accuracy": None,
            "type": {"name": "normal"},
            "effect_entries": [
                {"language": {"name": "en"}, "short_effect": "Sharply raises Attack.", "effect": "Boosts the user's Attack by two stages."}
            ],
        },
        "hydro-pump": {
            "damage_class": {"name": "special"},
            "power": 110,
            "accuracy": 80,
            "type": {"name": "water"},
            "effect_entries": [
                {"language": {"name": "en"}, "short_effect": "Powerful water blast.", "effect": "High power but low accuracy."}
            ],
        },
        "thunderbolt": {
            "damage_class": {"name": "special"},
            "power": 90,
            "accuracy": 100,
            "type": {"name": "electric"},
            "effect_entries": [
                {"language": {"name": "en"}, "short_effect": "May paralyze the target.", "effect": "Deals damage with a chance to paralyze."}
            ],
        },
        "hurricane": {
            "damage_class": {"name": "special"},
            "power": 110,
            "accuracy": 70,
            "type": {"name": "flying"},
            "effect_entries": [
                {"language": {"name": "en"}, "short_effect": "May confuse the target.", "effect": "Hits even during Fly."}
            ],
        },
    }

    species_entries = {
        445: {
            "egg_groups": [{"name": "monster"}, {"name": "dragon"}],
            "hatch_counter": 40,
            "gender_rate": 4,
            "evolution_chain": {"url": "https://pokeapi.co/api/v2/evolution-chain/222"},
        },
        25: {
            "egg_groups": [{"name": "ground"}],
            "hatch_counter": 10,
            "gender_rate": 4,
            "evolution_chain": {"url": "https://pokeapi.co/api/v2/evolution-chain/1337"},
        },
        130: {
            "egg_groups": [{"name": "water2"}],
            "hatch_counter": 20,
            "gender_rate": 4,
            "evolution_chain": {"url": "https://pokeapi.co/api/v2/evolution-chain/555"},
        },
    }

    evolution_chains = {
        "https://pokeapi.co/api/v2/evolution-chain/222": {
            "chain": {
                "species": {"name": "gible"},
                "evolves_to": [
                    {
                        "species": {"name": "gabite"},
                        "evolution_details": [{"min_level": 24, "trigger": {"name": "level-up"}}],
                        "evolves_to": [
                            {
                                "species": {"name": "garchomp"},
                                "evolution_details": [{"min_level": 48, "trigger": {"name": "level-up"}}],
                                "evolves_to": [],
                            }
                        ],
                    }
                ],
            }
        },
        "https://pokeapi.co/api/v2/evolution-chain/1337": {
            "chain": {"species": {"name": "pichu"}, "evolves_to": []}
        },
        "https://pokeapi.co/api/v2/evolution-chain/555": {
            "chain": {"species": {"name": "magikarp"}, "evolves_to": []}
        },
    }

    encounter_entries = {
        445: [
            {
                "location_area": {"name": "victory-road"},
                "version_details": [
                    {
                        "version": {"name": "omega-ruby"},
                        "max_chance": 15,
                        "encounter_details": [
                            {
                                "method": {"name": "walk"},
                                "min_level": 48,
                                "max_level": 50,
                                "chance": 15,
                                "condition_values": [{"name": "night"}],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    def fake_fetch_json(url: str, context: str) -> Dict[str, Any]:
        if url.endswith("/type"):
            return {"results": [{"name": t} for t in type_list]}
        if "/type/" in url:
            type_name = url.rstrip("/").split("/")[-1]
            if type_name in type_relations:
                return {"damage_relations": type_relations[type_name]}
        if "/ability/" in url:
            ability_name = url.rstrip("/").split("/")[-1]
            if ability_name in ability_entries:
                return ability_entries[ability_name]
        if "/pokemon-species/" in url:
            dex = int(url.rstrip("/").split("/")[-1])
            if dex in species_entries:
                return species_entries[dex]
        if "/evolution-chain/" in url:
            chain_url = url.rstrip("/")
            if chain_url in evolution_chains:
                return evolution_chains[chain_url]
        if "/pokemon/" in url and url.endswith("/encounters"):
            dex = int(url.split("/")[-2])
            if dex in encounter_entries:
                return encounter_entries[dex]
        if "/move/" in url:
            move_name = url.rstrip("/").split("/")[-1]
            if move_name in move_entries:
                return move_entries[move_name]
        raise AssertionError(f"Unexpected URL {url} requested for context {context}")

    monkeypatch.setattr(api, "_fetch_json", fake_fetch_json)


@pytest.fixture
def pokemon_registry() -> Dict[str, StubPokemon]:
    # Expose registry for tests that need to inspect raw fixtures.
    base_stats = StubBaseStats(hp=108, attack=130, defense=95, sp_atk=80, sp_def=85, speed=102)
    garchomp_moves = {
        "omega-ruby-alpha-sapphire": [
            StubMove("dragon-claw", "level-up", level=24),
            StubMove("earthquake", "level-up", level=48),
            StubMove("stone-edge", "tutor", None),
            StubMove("swords-dance", "level-up", level=36),
        ],
        "sun-moon": [
            StubMove("iron-tail", "egg", None),
            StubMove("hydro-pump", "egg", None),
        ],
    }
    descriptions = {
        "en": {
            "omega-ruby": "It flies at sonic speed, taking on its foes head-on.",
        }
    }
    garchomp = StubPokemon(
        name="garchomp",
        dex=445,
        types=["dragon", "ground"],
        base_stats=base_stats,
        moves=garchomp_moves,
        abilities=[
            SimpleNamespace(name="sand-veil", is_hidden=False),
            SimpleNamespace(name="rough-skin", is_hidden=True),
        ],
        descriptions=descriptions,
        height_dm=19,
        weight_hg=950,
        base_experience=270,
    )
    return {"garchomp": garchomp}


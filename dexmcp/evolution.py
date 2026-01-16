from __future__ import annotations

from typing import Dict, List, Optional

from . import api
from .models import EvolutionPath, EvolutionReport, EvolutionStep


def _expand_chain(
    node: Dict,
    current_path: List[EvolutionStep],
    all_paths: List[EvolutionPath],
) -> None:
    # Depth-first traversal that collects every evolution path through the chain graph.
    species_name = node["species"]["name"]
    evolves_to = node.get("evolves_to", [])
    if not evolves_to:
        all_paths.append(EvolutionPath(steps=current_path.copy()))
        return

    for child in evolves_to:
        evolution_details = child.get("evolution_details") or [{}]
        for detail in evolution_details:
            conditions: Dict[str, Optional[str]] = {}
            for key, value in detail.items():
                if key in {"trigger", "min_level", "item"}:
                    continue
                if key == "time_of_day" and value:
                    conditions[key] = value
                elif isinstance(value, dict):
                    conditions[key] = value.get("name")
                elif value not in (None, False):
                    conditions[key] = str(value)
            step = EvolutionStep(
                from_species=species_name,
                to_species=child["species"]["name"],
                trigger=(detail.get("trigger") or {}).get("name"),
                minimum_level=detail.get("min_level"),
                item=(detail.get("item") or {}).get("name"),
                conditions=conditions,
            )
            current_path.append(step)
            _expand_chain(child, current_path, all_paths)
            current_path.pop()


def plan_evolutions(name_or_dex: str) -> EvolutionReport:
    """Enumerate evolution paths for the given Pokemon."""
    pk = api._lookup(name_or_dex)
    species_data = api._fetch_json(
        f"https://pokeapi.co/api/v2/pokemon-species/{pk.dex}",
        context=f"species data for {pk.name}",
    )
    chain_url = species_data.get("evolution_chain", {}).get("url")
    if not chain_url:
        return EvolutionReport(pokemon=pk.name, paths=[])

    chain_data = api._fetch_json(chain_url, context="evolution chain")
    all_paths: List[EvolutionPath] = []
    _expand_chain(chain_data["chain"], [], all_paths)

    relevant_paths = [
        path
        for path in all_paths
        if any(step.from_species == pk.name or step.to_species == pk.name for step in path.steps)
    ]
    if not relevant_paths:
        relevant_paths = all_paths

    return EvolutionReport(pokemon=pk.name, paths=relevant_paths)

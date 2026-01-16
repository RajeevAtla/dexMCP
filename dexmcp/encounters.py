"""Encounter lookup helpers for PokeAPI data."""

from __future__ import annotations

from typing import List

from . import api
from .models import EncounterDetail, EncounterLocation, EncounterReport, EncounterVersion


def find_encounters(name_or_dex: str) -> EncounterReport:
    """Retrieve wild encounter locations from PokeAPI.

    Args:
        name_or_dex: Pokemon name or national dex number.

    Returns:
        Encounter report grouped by location and game version.
    """
    # Useful for players planning hunts or resource runs in a specific game version.
    pk = api._lookup(name_or_dex)
    data = api._fetch_json(
        f"https://pokeapi.co/api/v2/pokemon/{pk.dex}/encounters",
        context=f"encounter data for {pk.name}",
    )
    locations: List[EncounterLocation] = []
    for entry in data:
        location_area = entry.get("location_area", {}).get("name")
        versions: List[EncounterVersion] = []
        for version_detail in entry.get("version_details", []):
            version_name = version_detail.get("version", {}).get("name")
            max_chance = version_detail.get("max_chance", 0)
            details: List[EncounterDetail] = []
            for detail in version_detail.get("encounter_details", []):
                details.append(
                    EncounterDetail(
                        method=(detail.get("method") or {}).get("name", "unknown"),
                        min_level=detail.get("min_level", 0),
                        max_level=detail.get("max_level", 0),
                        chance=detail.get("chance", 0),
                        condition_values=[
                            value.get("name")
                            for value in detail.get("condition_values", [])
                            if value
                        ],
                    )
                )
            versions.append(
                EncounterVersion(
                    version=version_name,
                    max_chance=max_chance,
                    details=details,
                )
            )
        locations.append(
            EncounterLocation(
                location_area=location_area,
                versions=versions,
            )
        )
    return EncounterReport(pokemon=pk.name, locations=locations)

"""Targeted tests for dexmcp.breeding helpers.

These tests cover small utility functions used by the breeding helpers.
"""

from __future__ import annotations

import dexmcp.breeding as breeding


def test_gender_from_rate_handles_genderless() -> None:
    """Convert genderless rate to zeroed percentages.

    Genderless species should report 0% female and 0% male.
    """
    # The gender rate of -1 indicates a genderless Pokemon.
    gender = breeding._gender_from_rate(-1)
    assert gender.female_percent == 0.0
    assert gender.male_percent == 0.0

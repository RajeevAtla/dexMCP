"""Targeted tests for server module entrypoint.

These tests verify that running the module as a script triggers FastMCP.run
without starting a real server during the test suite.
"""

from __future__ import annotations

import runpy
import sys

import pytest


def test_server_main_invokes_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invoke the __main__ path without starting a real server.

    Uses a monkeypatched FastMCP.run to confirm the entrypoint executes.
    """
    called = {"run": False}

    def fake_run(self) -> None:
        called["run"] = True

    # Ensure a clean import path so runpy doesn't warn about reusing the module.
    sys.modules.pop("dexmcp.server", None)
    # Patch the FastMCP.run method to avoid launching a live server.
    monkeypatch.setattr("mcp.server.fastmcp.FastMCP.run", fake_run)
    # Execute the module as __main__ to hit the entrypoint guard.
    runpy.run_module("dexmcp.server", run_name="__main__")
    assert called["run"]

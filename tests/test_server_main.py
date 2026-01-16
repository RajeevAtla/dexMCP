"""Targeted tests for server module entrypoint."""

from __future__ import annotations

import runpy
import sys

import pytest


def test_server_main_invokes_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invoke the __main__ path without starting a real server."""
    called = {"run": False}

    def fake_run(self) -> None:
        called["run"] = True

    # Ensure a clean import path so runpy doesn't warn about reusing the module.
    sys.modules.pop("dexmcp.server", None)
    monkeypatch.setattr("mcp.server.fastmcp.FastMCP.run", fake_run)
    runpy.run_module("dexmcp.server", run_name="__main__")
    assert called["run"]

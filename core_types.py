"""Minimal shim for Python 3.13 rich imports used by Gradio CLI."""

from __future__ import annotations

from types import FrameType, MappingProxyType, ModuleType, TracebackType

__all__ = [
    "FrameType",
    "MappingProxyType",
    "ModuleType",
    "TracebackType",
]

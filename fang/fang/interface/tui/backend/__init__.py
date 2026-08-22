"""Backend bridge for external TUI clients."""

from fang.interface.tui.backend.controller import TuiController
from fang.interface.tui.backend.server import TuiBackendServer


__all__ = ["TuiBackendServer", "TuiController"]

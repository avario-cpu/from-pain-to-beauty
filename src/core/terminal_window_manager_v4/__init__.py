"""
Module for managing terminal windows. Usage is to create an instance of
TerminalWindowManager and use its methods to adjust the windows of the script.
"""

from .core.constants import TERMINAL_WINDOW_SLOTS_DB_FILE_PATH
from .core.twm_main import TerminalWindowManager
from .core.types import SecondaryWindow, WinType

__all__ = [
    "TerminalWindowManager",
    "SecondaryWindow",
    "WinType",
    "TERMINAL_WINDOW_SLOTS_DB_FILE_PATH",
]

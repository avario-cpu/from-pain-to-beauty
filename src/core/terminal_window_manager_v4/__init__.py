"""
Module for managing terminal windows. Usage is to create an instance of
TerminalWindowManager and use its methods to adjust the windows of the script.
"""

from .core.twm_main import TerminalWindowManager
from .core.types import SecondaryWindow, WinType

__all__ = ["TerminalWindowManager", "SecondaryWindow", "WinType"]

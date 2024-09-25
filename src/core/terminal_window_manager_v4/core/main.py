from typing import List, Optional

import aiosqlite

from src.core.terminal_window_manager_v4.core.types import SecondaryWindow, WinType
from src.core.terminal_window_manager_v4.helpers.window_adjuster import WindowAdjuster
from src.core.terminal_window_manager_v4.helpers.window_foreground_manager import (
    WindowForegroundManager,
)
from src.core.terminal_window_manager_v4.helpers.window_manager import WindowManager
from src.core.terminal_window_manager_v4.helpers.window_properties_calculator import (
    WindowPropertiesCalculator,
)
from src.core.terminal_window_manager_v4.helpers.window_refitter import WindowRefitter
from src.utils.helpers import construct_script_name
from src.utils.logging_utils import setup_logger

SCRIPT_NAME = construct_script_name(__file__)
logger = setup_logger(SCRIPT_NAME, "DEBUG")


class TerminalWindowManager:
    def __init__(self) -> None:
        self.adjuster = WindowAdjuster(logger=logger)
        self.calculator = WindowPropertiesCalculator(logger=logger)
        self.manager = WindowManager(self.adjuster, self.calculator, logger)
        self.foreground_manager = WindowForegroundManager(self.adjuster, logger)
        self.refitter = WindowRefitter(
            calculator=self.calculator,
            adjuster=self.adjuster,
            foreground_manager=self.foreground_manager,
            logger=logger,
        )

    async def adjust_window(
        self, conn: aiosqlite.Connection, window_type: WinType, window_name: str
    ) -> tuple[Optional[int], str]:
        slot, name = await self.manager.manage_window(conn, window_type, window_name)
        logger.info(f"Adjusted window <{window_name}> of type {window_type.name}.")
        return slot, name

    async def adjust_secondary_windows(
        self,
        slot: int,
        secondary_windows: List[SecondaryWindow],
    ) -> None:
        await self.manager.manage_secondary_windows(slot, secondary_windows)
        logger.info(f"Adjusted secondary windows for slot {slot}.")

    async def bring_windows_to_foreground(
        self, conn: aiosqlite.Connection, server: Optional[bool] = False
    ) -> None:
        await self.foreground_manager.bring_windows_to_foreground(conn, server)
        logger.info("Brought windows to foreground.")

    async def refit_all_windows(self, conn: aiosqlite.Connection) -> None:
        await self.refitter.refit_all_windows(conn)
        logger.info("Refitted all windows.")

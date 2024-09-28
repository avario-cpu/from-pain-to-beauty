from logging import Logger
from typing import Optional

import aiosqlite

from src.core import slots_db_handler as sdh
from src.core.terminal_window_manager_v4.core.constants import (
    MAIN_WINDOW_HEIGHT,
    MAIN_WINDOW_WIDTH,
    SERVER_WINDOW_NAME,
    WINDOW_NAME_SUFFIX,
)
from src.core.terminal_window_manager_v4.core.types import SecondaryWindow, WinType
from src.core.terminal_window_manager_v4.helpers.window_adjuster import WindowAdjuster
from src.core.terminal_window_manager_v4.helpers.window_properties_calculator import (
    WindowPropertiesCalculator,
)


class WindowManager:
    def __init__(
        self,
        adjuster: WindowAdjuster,
        calculator: WindowPropertiesCalculator,
        logger: Logger,
    ) -> None:
        self.adjuster = adjuster
        self.calculator = calculator
        self.logger = logger

    def generate_window_data(
        self, title: str, secondary_windows: Optional[list[SecondaryWindow]]
    ) -> list[tuple[str, int, int]]:
        data = [(title, MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)]
        if secondary_windows:
            for window in secondary_windows:
                sw_tuple = (window.name, window.width, window.height)
                data.append(sw_tuple)
        return data

    async def manage_secondary_windows(
        self, slot: int, secondary_windows: list[SecondaryWindow]
    ) -> None:
        properties = self.calculator.calculate_secondary_window_properties(
            slot, secondary_windows
        )
        for window, props in zip(secondary_windows, properties):
            await self.adjuster.adjust_window(window.name, props)
        self.logger.info(f"Secondary windows managed for slot {slot}.")

    async def manage_window(
        self,
        conn: aiosqlite.Connection,
        window_type: WinType,
        window_name: str,
        secondary_windows: Optional[list[SecondaryWindow]] = None,
    ) -> tuple[Optional[int], str]:
        """Main method to manage the main window of the script."""

        window_name = WINDOW_NAME_SUFFIX + window_name
        slot, title = await self.assign_slot_and_name_window(
            conn, window_type, window_name
        )

        properties = self.calculator.calculate_main_window_properties(window_type, slot)
        await self.adjuster.adjust_window(title, properties)

        if window_type == WinType.ACCEPTED and slot is not None:
            data = self.generate_window_data(title, secondary_windows)
            await sdh.occupy_slot_with_data(conn, slot, data)

        self.logger.info(f"Window <{window_name}> managed successfully.")
        return slot, window_name

    async def assign_slot_and_name_window(
        self, conn: aiosqlite.Connection, window_type: WinType, window_name: str
    ) -> tuple[Optional[int], str]:
        if window_type == WinType.ACCEPTED:
            slot_id = await sdh.get_first_free_slot(conn)
            if slot_id is None:
                raise ValueError("No available slot for an accepted window.")
            title = window_name
            self.adjuster.set_window_title(title)

        elif window_type == WinType.DENIED:
            slot_id = await sdh.occupy_first_free_denied_slot(conn)
            if slot_id is None:
                raise ValueError("No available slot for a denied window.")
            title = f"{window_name}_denied({slot_id})"
            self.adjuster.set_window_title(title)

        elif window_type == WinType.SERVER:
            slot_id = None  # Server doesn't occupy a slot in the DB
            title = SERVER_WINDOW_NAME
            self.adjuster.set_window_title(title)

        return slot_id, title

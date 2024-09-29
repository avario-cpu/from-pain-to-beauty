from logging import Logger

import aiosqlite

from src.core.terminal_window_manager_v4 import slots_db_handler as sdh
from src.core.terminal_window_manager_v4.core.types import SecondaryWindow, WinType
from src.core.terminal_window_manager_v4.helpers.window_adjuster import WindowAdjuster
from src.core.terminal_window_manager_v4.helpers.window_foreground_manager import (
    WindowForegroundManager,
)
from src.core.terminal_window_manager_v4.helpers.window_properties_calculator import (
    WindowPropertiesCalculator,
)


class WindowRefitter:
    def __init__(
        self,
        calculator: WindowPropertiesCalculator,
        adjuster: WindowAdjuster,
        foreground_manager: WindowForegroundManager,
        logger: Logger,
    ) -> None:
        self.calculator = calculator
        self.adjuster = adjuster
        self.foreground_manager = foreground_manager
        self.logger = logger

    async def search_for_vacant_slots(
        self, conn: aiosqlite.Connection
    ) -> dict[int, int]:
        free_slots = await sdh.get_all_free_slots(conn)
        occupied_slots = await sdh.get_all_occupied_slots(conn)
        occupied_slots.reverse()
        pairs = {}
        shorter_length = min(len(free_slots), len(occupied_slots))
        if free_slots:
            for i in range(shorter_length):
                current_slot = occupied_slots[i]
                new_slot = free_slots[i]
                if current_slot > free_slots[i]:
                    pairs[current_slot] = new_slot
        if pairs:
            self.logger.info(f"Vacant pairs found: {pairs}")
        else:
            self.logger.info("No Vacant pairs found")
        return pairs

    async def readjust_main_window(self, slot: int, title: str) -> None:
        props = self.calculator.calculate_main_window_properties(WinType.ACCEPTED, slot)
        await self.adjuster.adjust_window(title, props)

    async def readjust_secondary_windows(
        self, free_slot: int, data: list[tuple[str, int, int]]
    ) -> None:
        secondary_windows = [
            SecondaryWindow(data[i][0], data[i][1], data[i][2])
            for i in range(1, len(data))
        ]

        properties = self.calculator.calculate_secondary_window_properties(
            free_slot, secondary_windows
        )

        for window, props in zip(secondary_windows, properties):
            await self.adjuster.adjust_window(window.name, props)

    async def reset_windows_positions(self, conn: aiosqlite.Connection) -> None:
        occupied_slots = await sdh.get_all_occupied_slots(conn)
        for slot in occupied_slots:
            data = await sdh.get_full_data(conn, slot)
            self.logger.info(f"Rearrangement data obtained for slot {slot}: {data}")

            if data is not None and len(data) > 0 and len(data[0]) > 0:
                await self.readjust_main_window(slot, data[0][0])
                await self.readjust_secondary_windows(slot, data)

    async def refit_all_windows(self, conn: aiosqlite.Connection) -> None:
        self.logger.info("Refitting all windows...")
        pairs = await self.search_for_vacant_slots(conn) or {}

        for slot, new_slot in pairs.items():
            data = await sdh.get_full_data(conn, slot)
            self.logger.info(f"Rearrangement data obtained: {data}")

            if data is not None and len(data) > 0 and len(data[0]) > 0:
                await sdh.free_slot(conn, slot)
                await sdh.occupy_slot_with_data(conn, new_slot, data)
                await self.readjust_main_window(new_slot, data[0][0])
                await self.readjust_secondary_windows(new_slot, data)

        await self.reset_windows_positions(conn)
        await self.foreground_manager.bring_windows_to_foreground(conn)
        self.logger.info("Windows refitted.")

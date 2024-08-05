import asyncio
import os
import subprocess
import time
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

import aiosqlite
import pygetwindow as gw  # type: ignore
import win32con
import win32gui

from src.core import slots_db_handler as sdh
from src.core.constants import SERVER_WINDOW_NAME, TERMINAL_WINDOW_SLOTS_DB_FILE_PATH
from src.utils.helpers import construct_script_name
from src.utils.logging_utils import setup_logger

MAIN_WINDOW_WIDTH = 600
MAIN_WINDOW_HEIGHT = 260
MAX_WINDOWS_PER_COLUMN = 1040 // MAIN_WINDOW_HEIGHT  # So currently 4

SCRIPT_NAME = construct_script_name(__file__)
WINDOW_NAME_SUFFIX = "twm_"

logger = setup_logger(SCRIPT_NAME, "DEBUG")


class WinType(Enum):
    DENIED = auto()
    ACCEPTED = auto()
    SERVER = auto()


class SecondaryWindow:
    def __init__(self, name: str, width: int, height: int) -> None:
        self.name = name
        self.width = width
        self.height = height


class WindowAdjuster:
    async def find_window(
        self, title: str, timeout: int = 2
    ) -> Optional[gw.Win32Window]:
        start_time = time.time()
        duration = 0.0
        while duration < timeout:
            window = gw.getWindowsWithTitle(title)
            if window:
                return window[0]
            await asyncio.sleep(0.01)
            duration = time.time() - start_time
        logger.warning(f"Window <{title}> not found within {timeout}s.")
        return None

    async def adjust_window(
        self,
        title: str,
        properties: Tuple[int, int, int, int],
        resize: bool = True,
        move: bool = True,
    ) -> None:
        window = await self.find_window(title)
        if window:
            window.restore()
            if resize:
                window.resizeTo(properties[0], properties[1])
            if move:
                window.moveTo(properties[2], properties[3])
            logger.info(f"Window <{title}> adjusted successfully.")
        else:
            logger.error(f"Was not able to adjust window {title}.")

    def set_window_title(self, title: str) -> None:
        os.system(f"title {title}")
        logger.info(f"Window title set to <{title}>.")


class WindowForegroundManager:
    def __init__(self, adjuster: WindowAdjuster) -> None:
        self.adjuster = adjuster

    async def set_windows_to_topmost(
        self, conn: aiosqlite.Connection, server: Optional[bool] = False
    ) -> None:
        windows_names = (
            await sdh.get_all_names(conn) if not server else [SERVER_WINDOW_NAME]
        )
        windows_names.reverse()
        for name in windows_names:
            window = win32gui.FindWindow(None, name)
            if window:
                win32gui.SetWindowPos(
                    window,
                    win32con.HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                )
        logger.info("Windows set to topmost.")

    async def unset_windows_to_topmost(
        self, conn: aiosqlite.Connection, server: Optional[bool] = False
    ) -> None:
        windows_names = (
            await sdh.get_all_names(conn) if not server else [SERVER_WINDOW_NAME]
        )
        for name in windows_names:
            window = win32gui.FindWindow(None, name)
            if window:
                win32gui.SetWindowPos(
                    window,
                    win32con.HWND_NOTOPMOST,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                )
        logger.info("Windows unset from topmost.")

    async def restore_all_windows(
        self, conn: aiosqlite.Connection, server: Optional[bool] = False
    ) -> None:
        windows_names = (
            await sdh.get_all_names(conn) if not server else [SERVER_WINDOW_NAME]
        )
        for name in windows_names:
            window = gw.getWindowsWithTitle(name)
            if window:
                window = window[0]
                window.restore()
        logger.info("All windows restored.")

    async def bring_windows_to_foreground(
        self, conn: aiosqlite.Connection, server: Optional[bool] = False
    ) -> None:
        await self.restore_all_windows(conn, server)
        await self.set_windows_to_topmost(conn, server)
        await self.unset_windows_to_topmost(conn, server)
        logger.info("Windows brought to foreground.")


class WindowPropertiesCalculator:
    def calculate_main_window_properties(
        self, window_type: WinType, slot: Optional[int] = None
    ) -> Tuple[int, int, int, int]:
        if slot is not None and window_type in (WinType.ACCEPTED, WinType.DENIED):
            width = MAIN_WINDOW_WIDTH
            height = MAIN_WINDOW_HEIGHT

            if window_type == WinType.ACCEPTED:
                x_pos = -width * (1 + slot // MAX_WINDOWS_PER_COLUMN)
            elif window_type == WinType.DENIED:
                x_pos = -1920 + width * (slot // MAX_WINDOWS_PER_COLUMN)

            y_pos = height * (slot % MAX_WINDOWS_PER_COLUMN)

        elif window_type is WinType.SERVER:
            width = 700
            height = 400
            x_pos = -1920
            y_pos = 640

        logger.info(
            f"Calculated properties for {window_type.name} window at slot {slot}: "
            f"({width}, {height}, {x_pos}, {y_pos})."
        )

        return width, height, x_pos, y_pos

    def calculate_secondary_window_properties(
        self, slot: int, secondary_windows: List[SecondaryWindow]
    ) -> List[Tuple[int, int, int, int]]:
        properties = []
        x_pos_offset = MAIN_WINDOW_WIDTH
        y_pos_offset = 0

        for window in secondary_windows:
            width = window.width
            height = window.height

            if x_pos_offset - width < 0:
                x_pos_offset = MAIN_WINDOW_WIDTH
                y_pos_offset += height

            x_pos = (
                x_pos_offset
                - width
                - MAIN_WINDOW_WIDTH * (1 + slot // MAX_WINDOWS_PER_COLUMN)
            )
            y_pos = y_pos_offset + (
                MAIN_WINDOW_HEIGHT * (slot % MAX_WINDOWS_PER_COLUMN)
            )

            props = (width, height, x_pos, y_pos)
            properties.append(props)

            x_pos_offset -= width

        logger.info(
            f"Secondary properties for {[window.name for window in secondary_windows]} "
            f"calculated are {properties}"
        )

        return properties


class WindowRefitter:
    def __init__(
        self,
        calculator: WindowPropertiesCalculator,
        adjuster: WindowAdjuster,
        manager: "WindowManager",
    ) -> None:
        self.calculator = calculator
        self.adjuster = adjuster
        self.manager = manager

    async def search_for_vacant_slots(
        self, conn: aiosqlite.Connection
    ) -> Dict[int, int]:
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
            logger.info(f"Vacant pairs found: {pairs}")
        else:
            logger.info("No Vacant pairs found")
        return pairs

    async def readjust_main_window(self, slot: int, title: str) -> None:
        props = self.calculator.calculate_main_window_properties(WinType.ACCEPTED, slot)
        await self.adjuster.adjust_window(title, props)

    async def readjust_secondary_windows(
        self, free_slot: int, data: List[Tuple[str, int, int]]
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
            logger.info(f"Rearrangement data obtained for slot {slot}: {data}")

            if data is not None and len(data) > 0 and len(data[0]) > 0:
                await self.readjust_main_window(slot, data[0][0])
                await self.readjust_secondary_windows(slot, data)

    async def refit_all_windows(self, conn: aiosqlite.Connection) -> None:
        logger.info("Refitting all windows...")
        pairs = await self.search_for_vacant_slots(conn) or {}

        for slot, new_slot in pairs.items():
            data = await sdh.get_full_data(conn, slot)
            logger.info(f"Rearrangement data obtained: {data}")

            if data is not None and len(data) > 0 and len(data[0]) > 0:
                await sdh.free_slot(conn, slot)
                await sdh.occupy_slot_with_data(conn, new_slot, data)
                await self.readjust_main_window(new_slot, data[0][0])
                await self.readjust_secondary_windows(new_slot, data)

        await self.reset_windows_positions(conn)
        await self.manager.bring_windows_to_foreground(conn)
        logger.info("Windows refitted.")


class WindowManager:
    def __init__(
        self, adjuster: WindowAdjuster, calculator: WindowPropertiesCalculator
    ) -> None:
        self.adjuster = adjuster
        self.calculator = calculator

    def generate_window_data(
        self, title: str, secondary_windows: Optional[List[SecondaryWindow]]
    ) -> List[Tuple[str, int, int]]:
        data = [(title, MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)]
        if secondary_windows:
            for window in secondary_windows:
                sw_tuple = (window.name, window.width, window.height)
                data.append(sw_tuple)
        return data

    async def manage_secondary_windows(
        self, slot: int, secondary_windows: List[SecondaryWindow]
    ) -> None:
        properties = self.calculator.calculate_secondary_window_properties(
            slot, secondary_windows
        )
        for window, props in zip(secondary_windows, properties):
            await self.adjuster.adjust_window(window.name, props)
        logger.info(f"Secondary windows managed for slot {slot}.")

    async def manage_window(
        self,
        conn: aiosqlite.Connection,
        window_type: WinType,
        window_name: str,
        secondary_windows: Optional[List[SecondaryWindow]] = None,
    ) -> Tuple[Optional[int], str]:
        window_name = WINDOW_NAME_SUFFIX + window_name
        slot, title = await self.assign_slot_and_name_window(
            conn, window_type, window_name
        )

        properties = self.calculator.calculate_main_window_properties(window_type, slot)
        await self.adjuster.adjust_window(title, properties)

        if window_type == WinType.ACCEPTED and slot is not None:
            data = self.generate_window_data(title, secondary_windows)
            await sdh.occupy_slot_with_data(conn, slot, data)
        logger.info(f"Window <{window_name}> managed successfully.")
        return slot, window_name

    async def assign_slot_and_name_window(
        self, conn: aiosqlite.Connection, window_type: WinType, window_name: str
    ) -> Tuple[Optional[int], str]:

        if window_type == WinType.ACCEPTED:
            slot_id = await sdh.get_first_free_slot(conn)
            title = window_name
            self.adjuster.set_window_title(title)

        elif window_type == WinType.DENIED:
            slot_id = await sdh.occupy_first_free_denied_slot(conn)
            title = f"{window_name}_denied({slot_id})"
            self.adjuster.set_window_title(title)

        elif window_type is WinType.SERVER:
            slot_id = None  # server doesn't occupy a slot in the DB
            title = SERVER_WINDOW_NAME
            self.adjuster.set_window_title(title)

        return slot_id, title

    async def bring_windows_to_foreground(
        self, conn: aiosqlite.Connection, server: Optional[bool] = False
    ) -> None:
        foreground_manager = WindowForegroundManager(self.adjuster)
        await foreground_manager.bring_windows_to_foreground(conn, server)

    async def refit_all_windows(self, conn: aiosqlite.Connection) -> None:
        refitter = WindowRefitter(self.calculator, self.adjuster, self)
        await refitter.refit_all_windows(conn)


class MainManager:
    def __init__(self) -> None:
        self.adjuster = WindowAdjuster()
        self.calculator = WindowPropertiesCalculator()
        self.manager = WindowManager(self.adjuster, self.calculator)

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
        await self.manager.bring_windows_to_foreground(conn, server)
        logger.info("Brought windows to foreground.")

    async def refit_all_windows(self, conn: aiosqlite.Connection) -> None:
        await self.manager.refit_all_windows(conn)
        logger.info("Refitted all windows.")


async def main() -> None:
    """Either to demonstrate the repositionement when running this script from a separate terminal window or
    to demonstrate for multiple windows when this script is run as an individual subprocess.
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))

    # Paths to the batch files
    script_file1 = os.path.join(script_dir, "secondary_window1.py")
    script_file2 = os.path.join(script_dir, "secondary_window2.py")

    # Spawning two secondary windows
    subprocess.Popen(["python", script_file1])
    subprocess.Popen(["python", script_file2])

    await asyncio.sleep(1)  # Give some time for the windows to appear

    conn = await sdh.create_connection(TERMINAL_WINDOW_SLOTS_DB_FILE_PATH)
    if conn:
        main_manager = MainManager()
        slot, _ = await main_manager.adjust_window(
            conn, WinType.ACCEPTED, "Example Script"
        )
        if slot is not None:
            secondary_windows = [
                SecondaryWindow(name="Secondary Window 1", width=150, height=150),
                SecondaryWindow(name="Secondary Window 2", width=150, height=150),
            ]
            await main_manager.adjust_secondary_windows(slot, secondary_windows)

        await sdh.free_all_slots(conn)
        print("Adjusted.")
    else:
        print("Connection with DB failed to be established.")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
import time
from enum import Enum, auto
from typing import Optional

import aiosqlite
import pygetwindow as gw  # type: ignore
import win32con
import win32gui

from src.core import slots_db_handler as sdh
from src.core.constants import SERVER_WINDOW_NAME
from src.utils.helpers import construct_script_name
from src.utils.logging_utils import setup_logger

MAIN_WINDOW_WIDTH = 600
MAIN_WINDOW_HEIGHT = 260
MAX_WINDOWS_PER_COLUMN = 1040 // MAIN_WINDOW_HEIGHT  # So currently 4

SCRIPT_NAME = construct_script_name(__file__)
WINDOW_NAME_SUFFIX = "twm_"

logger = setup_logger(SCRIPT_NAME, "DEBUG")


class WinType(Enum):
    """Used to define the window to be managed. Position of said window
    will depend on whether the terminal is that of a normally running
    script (ACCEPTED), or that of a duplicated script, prevented from being
    run by a single instance lock (DENIED). SERVER gets a particular
    position, since there should only be one constantly running SERVER."""

    DENIED = auto()
    ACCEPTED = auto()
    SERVER = auto()


class SecondaryWindow:
    def __init__(self, name: str, width: int, height: int):
        self.name = name
        self.width = width
        self.height = height


async def get_all_windows_names(conn: aiosqlite.Connection) -> list[str]:
    names = await sdh.get_all_names(conn)
    return names


async def set_windows_to_topmost(
    conn: aiosqlite.Connection, server: Optional[bool] = False
):
    """Set the scripts windows to be on top of the screen."""
    windows_names = (
        await get_all_windows_names(conn) if not server else [SERVER_WINDOW_NAME]
    )
    print(windows_names)
    windows_names.reverse()  # helps with having secondary windows (who spawn
    # later) on top of the main terminal.
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


async def unset_windows_to_topmost(
    conn: aiosqlite.Connection, server: Optional[bool] = False
):
    """Set the scripts windows fore/background behavior back to normal."""
    windows_names = (
        await get_all_windows_names(conn) if not server else [SERVER_WINDOW_NAME]
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


async def restore_all_windows(
    conn: aiosqlite.Connection, server: Optional[bool] = False
):
    """Restore to normal size all windows who have been minimized/maximized"""
    windows_names = (
        await get_all_windows_names(conn) if not server else [SERVER_WINDOW_NAME]
    )
    for name in windows_names:
        window = gw.getWindowsWithTitle(name)
        if window:
            window = window[0]
            window.restore()


async def bring_windows_to_foreground(
    conn: aiosqlite.Connection, server: Optional[bool] = False
):
    """Bring the script windows to the foreground"""
    await restore_all_windows(conn, server)
    await set_windows_to_topmost(conn, server)
    await unset_windows_to_topmost(conn, server)


def set_window_title(title: str):
    os.system(f"title {title}")


async def find_window(title: str, timeout: int = 2) -> gw.Win32Window | None:
    """Find window by title within a given timeout"""
    start_time = time.time()
    duration = 0.0
    while duration < timeout:
        window = gw.getWindowsWithTitle(title)
        if window:
            return window[0]
        await asyncio.sleep(0.01)
        duration = time.time() - start_time
    logger.warning(f"Window '{title}' not found within {timeout}s.")
    return None


async def assign_slot_and_name_window(
    conn: Optional[aiosqlite.Connection], window_type: WinType, window_name: str
):
    """Assign a slot and sets window title based on window type."""
    if window_type == WinType.ACCEPTED:
        slot_id = await sdh.get_first_free_slot(conn)
        title = window_name
        set_window_title(title)
        return slot_id, title

    elif window_type == WinType.DENIED:
        slot_id = await sdh.occupy_first_free_denied_slot(conn)
        title = f"{window_name}_denied({slot_id})"
        set_window_title(title)
        return slot_id, title

    elif window_type is WinType.SERVER:
        # Server doesn't take a slot in the database
        title = SERVER_WINDOW_NAME
        set_window_title(title)
        return None, title


def calculate_main_window_properties(window_type: WinType, slot: int):
    """Calculates window size and position based on slot and type."""
    if window_type in (WinType.ACCEPTED, WinType.DENIED):

        width = MAIN_WINDOW_WIDTH
        height = MAIN_WINDOW_HEIGHT
        x_pos = (
            -width * (1 + slot // MAX_WINDOWS_PER_COLUMN)
            if window_type == WinType.ACCEPTED
            else -1920 + width * (slot // MAX_WINDOWS_PER_COLUMN)
        )
        y_pos = height * (slot % MAX_WINDOWS_PER_COLUMN)
        return width, height, x_pos, y_pos

    elif window_type is WinType.SERVER:
        width = 700
        height = 400
        x_pos = -1920
        y_pos = 640
        return width, height, x_pos, y_pos


def calculate_secondary_window_properties(
    slot: int, secondary_windows: list[SecondaryWindow]
) -> list[tuple[int, int, int, int]]:
    """Set properties for a list of secondary windows"""
    properties = []
    x_pos_offset = MAIN_WINDOW_WIDTH
    y_pos_offset = 0
    logger.debug(f"Calculating secondary properties for slot {slot}")

    for i in range(len(secondary_windows)):
        width = secondary_windows[i].width
        height = secondary_windows[i].height

        if x_pos_offset - width < 0:
            # move to the next line
            x_pos_offset = MAIN_WINDOW_WIDTH
            y_pos_offset += height

        x_pos = (
            x_pos_offset
            - width
            - MAIN_WINDOW_WIDTH * (1 + slot // MAX_WINDOWS_PER_COLUMN)
        )
        y_pos = y_pos_offset + (MAIN_WINDOW_HEIGHT * (slot % MAX_WINDOWS_PER_COLUMN))

        props = width, height, x_pos, y_pos
        properties.append(props)

        x_pos_offset -= width  # decrement x_pos_offset for the next window

    logger.info(
        f"Secondary properties for {[win.name for win in secondary_windows]} "
        f"calculated are {properties}"
    )

    return properties


async def adjust_window(
    title: str,
    properties: tuple[int, int, int, int],
    resize: bool = True,
    move: bool = True,
):
    """Adjust window position and size."""
    window = await find_window(title)
    if window:
        window.restore()
        if resize:
            window.resizeTo(properties[0], properties[1])
        if move:
            window.moveTo(properties[2], properties[3])
    else:
        logger.error(f"Was not able to adjust window {title}.")


def generate_window_data(
    title: str, secondary_windows: Optional[list[SecondaryWindow]]
):
    data = [(title, MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)]
    if secondary_windows:
        sw = secondary_windows
        for i in range(len(sw)):
            sw_tuple = sw[i].name, sw[i].width, sw[i].height
            data.append(sw_tuple)
    return data


async def search_for_vacant_slots(conn: aiosqlite.Connection) -> dict[int, int]:
    """Look if they are free slots available in the database before the ones
    currently occupied. E.g. slot 7 is occupied while slot 3 is free.
    :return: a dict with (occupied slot : free slot) pairs
    """
    free_slots = await sdh.get_all_free_slots(conn)
    occupied_slots = await sdh.get_all_occupied_slots(conn)
    occupied_slots.reverse()  # we want to match the highest occupied slot
    # with the lowest free slot
    pairs = {}
    shorter_length = min(len(free_slots), len(occupied_slots))
    if free_slots:
        for i in range(shorter_length):
            current_slot = occupied_slots[i]
            new_slot = free_slots[i]
            if current_slot > free_slots[i]:
                pairs[current_slot] = new_slot
            else:
                logger.debug(
                    f"Slot {new_slot} is free but comes later "
                    f"than latest occupied slot {current_slot}"
                )
    if pairs:
        logger.info(f"Vacant pairs found: {pairs}")
    else:
        logger.info("No Vacant pairs found")
    return pairs


async def readjust_main_window(slot: int, title: str):
    """Move and transform main window to a new slot"""
    props = calculate_main_window_properties(WinType.ACCEPTED, slot)
    await adjust_window(title, props)


async def readjust_secondary_windows(free_slot: int, data: list[tuple[str, int, int]]):
    secondary_windows = [
        SecondaryWindow(data[i][0], data[i][1], data[i][2]) for i in range(1, len(data))
    ]

    props = calculate_secondary_window_properties(free_slot, secondary_windows)

    for i in range(len(secondary_windows)):
        await adjust_window(secondary_windows[i].name, props[i])


async def reset_windows_positions(conn: aiosqlite.Connection):
    """Move all active windows back to their allocated positions"""
    occupied_slots = await sdh.get_all_occupied_slots(conn)
    for slot in occupied_slots:
        data = await sdh.get_full_data(conn, slot)
        logger.info(f"Rearrangement data obtained for slot {slot}: {data}")

        if data is not None and len(data) > 0 and len(data[0]) > 0:
            await readjust_main_window(slot, data[0][0])
            await readjust_secondary_windows(slot, data)


async def refit_all_windows(conn: aiosqlite.Connection):
    """Rearrange windows to fill empty slots in a more compact way. Also
    makes them return back to their position and to the foreground"""
    logger.info("Refitting all windows...")
    pairs = await search_for_vacant_slots(conn) or {}

    for slot, new_slot in pairs.items():
        data = await sdh.get_full_data(conn, slot)
        logger.info(f"Rearrangement data obtained: {data}")

        if data is not None and len(data) > 0 and len(data[0]) > 0:
            await sdh.free_slot(conn, slot)
            await sdh.occupy_slot_with_data(conn, new_slot, data)
            await readjust_main_window(new_slot, data[0][0])
            await readjust_secondary_windows(new_slot, data)

    await reset_windows_positions(conn)
    await bring_windows_to_foreground(conn)


async def manage_secondary_windows(slot: int, secondary_windows: list[SecondaryWindow]):
    """Fit secondary windows next to main one"""
    properties = calculate_secondary_window_properties(slot, secondary_windows)
    for i in range(0, len(secondary_windows)):
        await adjust_window(secondary_windows[i].name, properties[i])


async def manage_window(
    conn: Optional[aiosqlite.Connection],
    window_type: WinType,
    window_name: str,
    secondary_windows: Optional[list[SecondaryWindow]] = None,
) -> tuple[int | None, str]:
    """Assign a name to the window with a suffix, to avoid repositioning of
    the IDE window with the script open in it rather than the CLI...
    Then, assign a slot to the window in the database and resize and
    reposition it accordingly."""
    window_name = WINDOW_NAME_SUFFIX + window_name
    slot, title = await assign_slot_and_name_window(conn, window_type, window_name)

    properties = calculate_main_window_properties(window_type, slot)
    await adjust_window(title, properties)

    if window_type == WinType.ACCEPTED and slot is not None:
        data = generate_window_data(title, secondary_windows)
        await sdh.occupy_slot_with_data(conn, slot, data)
    return slot, window_name  # slot can be none in case of window_type SERVER


async def main():
    # Example usage
    conn = await sdh.create_connection("../../data/slots.db")
    await manage_window(conn, WinType.ACCEPTED, "Example Script")
    if conn:
        await sdh.free_all_slots(conn)


if __name__ == "__main__":
    asyncio.run(main())

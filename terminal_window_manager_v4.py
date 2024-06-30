import asyncio
import logging
import os
import time
from enum import Enum, auto

import aiosqlite
import pygetwindow as gw
import win32con
import win32gui
import my_utils

import constants as const
import denied_slots_db_handler as denied_sdh
import my_classes as my
import slots_db_handler as sdh
from constants import SERVER_WINDOW_NAME

MAIN_WINDOW_WIDTH = 600
MAIN_WINDOW_HEIGHT = 260
MAX_WINDOWS_PER_COLUMN = 1040 // MAIN_WINDOW_HEIGHT  # So currently 4

SCRIPT_NAME = my_utils.construct_script_name(__file__,
                                             const.SCRIPT_NAME_SUFFIX)

logger = my_utils.setup_logger(SCRIPT_NAME, logging.DEBUG)


class WinType(Enum):
    DENIED = auto()
    ACCEPTED = auto()
    SERVER = auto()


def window_exit_countdown(duration: int):
    """Give a bit of time to read terminal exit statements"""
    for seconds in reversed(range(1, duration)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    exit()


async def get_all_windows_names(conn: aiosqlite.Connection) -> list[str]:
    names = await sdh.get_all_names(conn)
    return names


async def set_windows_to_topmost(conn: aiosqlite.Connection):
    """Set the scripts windows to be on top of the screen."""
    windows_names = await get_all_windows_names(conn)
    windows_names.reverse()  # helps with having secondary windows (who spawn
    # later) on top of the main terminal.
    for name in windows_names:
        window = win32gui.FindWindow(None, name)
        if window:
            win32gui.SetWindowPos(window,
                                  win32con.HWND_TOPMOST,
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


async def unset_windows_to_topmost(conn: aiosqlite.Connection):
    """Set the scripts windows fore/background behavior back to normal."""
    windows_names = await get_all_windows_names(conn)
    for name in windows_names:
        window = win32gui.FindWindow(None, name)
        if window:
            win32gui.SetWindowPos(window,
                                  win32con.HWND_NOTOPMOST,
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


async def restore_all_windows(conn: aiosqlite.Connection):
    """Restore to normal size all windows who have been minimized/maximized"""
    windows_names = await get_all_windows_names(conn)
    for name in windows_names:
        window = gw.getWindowsWithTitle(name)
        if window:
            window = window[0]
            window.restore()


async def bring_windows_to_foreground(conn: aiosqlite.Connection):
    """Bring the script windows to the foreground"""
    await restore_all_windows(conn)
    await set_windows_to_topmost(conn)
    await unset_windows_to_topmost(conn)


def set_window_title(title: str):
    os.system(f"title {title}")


async def find_window(title: str, timeout: int = 2) -> gw.Win32Window | None:
    """Find window by title within a given timeout"""
    end_time = time.time() + timeout
    while time.time() < end_time:
        window = gw.getWindowsWithTitle(title)
        if window:
            return window[0]
        await asyncio.sleep(0.01)
    logger.warning(f"Window '{title}' not found within {timeout}s.")
    return None


async def assign_slot_and_name_window(conn: aiosqlite.Connection,
                                      window_type: WinType,
                                      window_name: str):
    """Assign a slot and sets window title based on window type."""
    if window_type == WinType.ACCEPTED:
        slot_id = await sdh.get_first_free_slot(conn)
        title = window_name
        set_window_title(title)
        return slot_id, title

    elif window_type == WinType.DENIED:
        slot_id = await denied_sdh.occupy_first_free_slot(conn)
        title = f"{window_name}_denied({slot_id})"
        set_window_title(title)
        return slot_id, title

    elif window_type is WinType.SERVER:
        # Server doesnt take a slot in the database
        title = SERVER_WINDOW_NAME
        set_window_title(title)
        return None, title


def calculate_main_window_properties(window_type: WinType, slot: int):
    """Calculates window size and position based on slot and type."""
    if window_type in (WinType.ACCEPTED, WinType.DENIED):

        width = MAIN_WINDOW_WIDTH
        height = MAIN_WINDOW_HEIGHT
        x_pos = -width * (1 + slot // MAX_WINDOWS_PER_COLUMN) \
            if window_type == WinType.ACCEPTED \
            else -1920 + width * (slot // MAX_WINDOWS_PER_COLUMN)
        y_pos = height * (slot % MAX_WINDOWS_PER_COLUMN)
        return width, height, x_pos, y_pos

    elif window_type is WinType.SERVER:
        width = 700
        height = 400
        x_pos = -1920
        y_pos = 640
        return width, height, x_pos, y_pos

    return None


def calculate_secondary_window_properties(
        slot: int, secondary_windows: list[my.SecondaryWindow]) \
        -> list[tuple[int, int, int, int]]:
    """Set properties for a list of secondary windows"""
    properties = []
    x_pos_offset = MAIN_WINDOW_WIDTH
    y_pos_offset = 0
    logger.debug(f"Calculating with slot {slot}")

    for i in range(len(secondary_windows)):
        width = secondary_windows[i].width
        height = secondary_windows[i].height

        if x_pos_offset - width < 0:
            # move to the next line
            x_pos_offset = MAIN_WINDOW_WIDTH
            y_pos_offset += height

        x_pos = (x_pos_offset - width -
                 MAIN_WINDOW_WIDTH * (1 + slot // MAX_WINDOWS_PER_COLUMN))
        y_pos = (y_pos_offset +
                 (MAIN_WINDOW_HEIGHT * (slot % MAX_WINDOWS_PER_COLUMN)))

        props = width, height, x_pos, y_pos
        properties.append(props)

        logger.info(f"Secondary properties calculated for "
                    f"'{secondary_windows[i].name}' are {props}")

        x_pos_offset -= width  # decrement x_pos_offset for the next window

    return properties


async def adjust_window(title: str,
                        properties: tuple[int, int, int, int],
                        resize: bool = True, move: bool = True):
    """Adjust window position and size."""
    window = await find_window(title)
    if window:
        window.restore()
        if resize:
            window.resizeTo(*properties[:2])
        if move:
            window.moveTo(*properties[2:])
    else:
        logger.error(f"Window {title} Not found.")


def generate_window_data(title: str,
                         secondary_windows: list[my.SecondaryWindow]):
    data = [(title, MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)]
    if secondary_windows:
        sw = secondary_windows
        for i in range(len(sw)):
            sw_tuple = sw[i].name, sw[i].width, sw[i].height
            data.append(sw_tuple)
    return data


async def search_for_vacant_slots(conn: aiosqlite.Connection) -> dict[int:int]:
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
                logger.info(f"Slot {new_slot} is free but comes later "
                            f"than latest occupied slot {current_slot}")
    logger.info(f"Vacant pairs founds: {pairs}")
    return pairs


async def readjust_main_window(slot: int, title: str):
    """Move and transform main window to a new slot"""
    props = calculate_main_window_properties(WinType.ACCEPTED, slot)
    await adjust_window(title, props)


async def readjust_secondary_windows(free_slot: int,
                                     data: list[tuple[str, int, int]]):
    secondary_windows = [
        my.SecondaryWindow(data[i][0], data[i][1], data[i][2]) for i in
        range(1, len(data))]

    props = calculate_secondary_window_properties(
        free_slot, secondary_windows)

    for i in range(len(secondary_windows)):
        await adjust_window(secondary_windows[i].name, props[i])


async def reset_windows_positions(conn: aiosqlite.Connection):
    """Move all active windows back to their allocated positions"""
    occupied_slots = await sdh.get_all_occupied_slots(conn)
    for slot in occupied_slots:
        data = await sdh.get_full_data(conn, slot)
        logger.info(f"Rearrangement data obtained for slot {slot}: {data}")
        await readjust_main_window(slot, data[0][0])
        await readjust_secondary_windows(slot, data)


async def refit_all_windows(conn: aiosqlite.Connection):
    """Rearrange windows to fill empty slots in a more compact way. Also
    makes them return back to their position and to the foreground"""
    pairs = await search_for_vacant_slots(conn) if not None else {}
    for slot, new_slot in pairs.items():
        data = await sdh.get_full_data(conn, slot)
        logger.info(f"Rearrangement data obtained: {data}")
        await sdh.free_slot(conn, slot)
        await sdh.occupy_slot_with_data(conn, new_slot, data)
        await readjust_main_window(new_slot, data[0][0])
        await readjust_secondary_windows(new_slot, data)
    await reset_windows_positions(conn)
    await bring_windows_to_foreground(conn)


async def manage_secondary_windows(
        slot: int, secondary_windows: list[my.SecondaryWindow]):
    """Fit secondary windows next to main one"""
    properties = calculate_secondary_window_properties(slot, secondary_windows)
    for i in range(0, len(secondary_windows)):
        await adjust_window(secondary_windows[i].name, properties[i])


async def manage_window(conn: aiosqlite.Connection,
                        window_type: WinType,
                        window_name: str,
                        secondary_windows: list[my.SecondaryWindow] = None):
    """Manage window allocation and positioning."""
    slot, title = await assign_slot_and_name_window(conn, window_type,
                                                    window_name)

    properties = calculate_main_window_properties(window_type, slot)
    await adjust_window(title, properties)

    if window_type == WinType.ACCEPTED and slot is not None:
        data = generate_window_data(title, secondary_windows)
        await sdh.occupy_slot_with_data(conn, slot, data)
    return slot


async def main():
    # Example usage
    conn = await sdh.create_connection("slots.db")
    await manage_window(conn, WinType.ACCEPTED, "Example Script")
    await sdh.free_all_slots(conn)


if __name__ == '__main__':
    asyncio.run(main())

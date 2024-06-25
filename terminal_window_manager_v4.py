import logging
import os
import time
from enum import Enum, auto

import pygetwindow as gw
import win32con
import win32gui

import denied_slots_db_handler as denied_sdh
import my_classes as my
import slots_db_handler as sdh
from constants import SERVER_WINDOW_NAME

logger = logging.getLogger('terminal_window_manager')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('temp/logs/twm_v4.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

logger.info('Start test for shop_watcher')

MAIN_WINDOW_WIDTH = 600
MAIN_WINDOW_HEIGHT = 260
MAX_WINDOWS_PER_COLUMN = 1040 // MAIN_WINDOW_HEIGHT  # considering taskbar


class WinType(Enum):
    DENIED = auto()
    ACCEPTED = auto()
    SERVER = auto()


def get_all_windows_names():
    names = sdh.get_all_names()
    return names


def set_windows_to_topmost():
    """Set the scripts windows to be on top of the screen."""
    windows_names = get_all_windows_names()
    windows_names.reverse()  # helps with having secondary windows (who spawn
    # later) on top of the main terminal.
    for name in windows_names:
        window = win32gui.FindWindow(None, name)
        if window:
            win32gui.SetWindowPos(window,
                                  win32con.HWND_TOPMOST,
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


def unset_windows_to_topmost():
    """Set the scripts windows fore/background behavior back to normal."""
    windows_names = get_all_windows_names()
    for name in windows_names:
        window = win32gui.FindWindow(None, name)
        if window:
            win32gui.SetWindowPos(window,
                                  win32con.HWND_NOTOPMOST,
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


def restore_all_windows():
    """Restore to normal size all windows who have been minimized/maximized"""
    windows_names = get_all_windows_names()
    for name in windows_names:
        window = gw.getWindowsWithTitle(name)
        if window:
            window = window[0]
            window.restore()


def bring_window_to_foreground():
    """Bring the script windows to the foreground"""
    restore_all_windows()
    set_windows_to_topmost()
    unset_windows_to_topmost()


def set_window_title(title):
    os.system(f"title {title}")


def find_window(title: str, timeout=3) -> gw.Win32Window | None:
    """Find window by title within a given timeout"""
    end_time = time.time() + timeout
    while time.time() < end_time:
        window = gw.getWindowsWithTitle(title)
        if window:
            return window[0]
        time.sleep(0.01)
    logger.warning(f"Window '{title}' not found within timeout.")
    return None


def find_slot_and_name_window(window_type: WinType, window_name: str):
    """Assign a slot and sets window title based on window type."""
    if window_type == WinType.ACCEPTED:
        slot_id = sdh.get_first_free_slot()
        title = window_name
        set_window_title(title)
        return slot_id, title

    elif window_type == WinType.DENIED:
        slot_id = denied_sdh.occupy_first_free_slot()
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
    x_pos_offset = 0

    for i in range(0, len(secondary_windows)):
        width = secondary_windows[i].width
        height = secondary_windows[i].height
        x_pos = (-width - MAIN_WINDOW_WIDTH * (slot // MAX_WINDOWS_PER_COLUMN)
                 + x_pos_offset)
        y_pos = MAIN_WINDOW_HEIGHT * (slot % MAX_WINDOWS_PER_COLUMN)

        props = width, height, x_pos, y_pos
        properties.append(props)
        logger.info(f"Secondary properties calculated are {props}")
        x_pos_offset -= width  # to avoid overlap

    return properties


def adjust_window(title: str,
                  properties: tuple[int, int, int, int],
                  resize=True, move=True):
    """Adjust window position and size."""
    window = find_window(title)
    if window:
        window.restore()
        if resize:
            window.resizeTo(*properties[:2])
        if move:
            window.moveTo(*properties[2:])
    else:
        logger.error("Window not found for adjusting position.")


def generate_window_data(title: str,
                         secondary_windows: list[my.SecondaryWindow]):
    data = [(title, MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)]
    if secondary_windows:
        sw = secondary_windows
        for i in range(len(sw)):
            sw_tuple = sw[i].name, sw[i].width, sw[i].height
            data.append(sw_tuple)
    return data


def search_for_vacant_slots() -> dict[int:int]:
    """Look if they are free slots available in the database before the ones
    currently occupied. E.g. slot 7 is occupied while slot 3 is free.
    :return: a dict with (occupied slot : free slot) pairs
    """
    free_slots = sdh.get_all_free_slots()
    occupied_slots = sdh.get_all_occupied_slots()
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


def rearrange_main_window(free_slot, data):
    main_properties = calculate_main_window_properties(WinType.ACCEPTED,
                                                       free_slot)
    adjust_window(data[0][0], main_properties)


def rearrange_secondary_windows(free_slot, data):
    secondary_windows = [
        my.SecondaryWindow(data[i][0], data[i][1], data[i][2]) for i in
        range(1, len(data))]

    secondary_properties = calculate_secondary_window_properties(
        free_slot, secondary_windows)

    for i in range(len(secondary_windows)):
        adjust_window(secondary_windows[i].name, secondary_properties[i])


def obtain_window_data(current_slot):
    """Obtain main and secondary window data from a database slot"""
    data = sdh.get_full_data(current_slot)
    data = [(data[i], data[i + 1], data[i + 2])
            for i in range(0, len(data) - 2, 3)
            if None not in (data[i], data[i + 1], data[i + 2])]
    # yea the expression is complicated, but you'll get it bro, read again :)
    logger.info(f"Rearrangement data obtained: {data}")
    return data


def refit_windows():
    """Move all active windows back to their allocated positions"""
    for active_window_slot in sdh.get_all_occupied_slots():
        data = obtain_window_data(active_window_slot)
        rearrange_main_window(active_window_slot, data)
        rearrange_secondary_windows(active_window_slot, data)


def rearrange_windows():
    """Rearrange windows to fill empty slots in a more compact way. Also
    makes them return back to their position and to the foreground"""
    pairs = search_for_vacant_slots() if not None else {}
    for current_slot, free_slot in pairs.items():
        data = obtain_window_data(current_slot)
        sdh.free_slot(current_slot)
        sdh.occupy_slot_with_data(free_slot, data)

        rearrange_main_window(free_slot, data)
        rearrange_secondary_windows(free_slot, data)
    refit_windows()
    bring_window_to_foreground()


def manage_secondary_windows(
        slot: int, secondary_windows: list[my.SecondaryWindow]):
    """Fit secondary windows next to main one"""
    properties = calculate_secondary_window_properties(slot, secondary_windows)
    for i in range(0, len(secondary_windows)):
        adjust_window(secondary_windows[i].name, properties[i])


def manage_window(window_type, window_name,
                  secondary_windows: list[my.SecondaryWindow] = None):
    """Manage window allocation and positioning."""
    slot, title = find_slot_and_name_window(window_type, window_name)

    properties = calculate_main_window_properties(window_type, slot)
    adjust_window(title, properties)

    if window_type == WinType.ACCEPTED and slot is not None:
        data = generate_window_data(title, secondary_windows)
        sdh.occupy_slot_with_data(slot, data)
    return slot


if __name__ == '__main__':
    logger.info("Window Manager Script Started")
    # Example usage
    manage_window(WinType.ACCEPTED, "Example Script")

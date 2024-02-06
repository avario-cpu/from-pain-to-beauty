import logging
import os
import time
from enum import Enum, auto
import pygetwindow as gw
import win32con
import win32gui
import denied_slots_db_handler as denied_sdh
import shop_watcher as sw
import slots_db_handler as sdh
from constants import SERVER_WINDOW_NAME

# Setup logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename="temp/logs/twm_v3.log")

MAIN_WINDOW_WIDTH = 600
MAIN_WINDOW_HEIGHT = 260
MAX_WINDOWS_PER_COLUMN = 1040 // MAIN_WINDOW_HEIGHT  # considering taskbar


class WindowType(Enum):
    DENIED_SCRIPT = auto()
    ACCEPTED_SCRIPT = auto()
    SERVER = auto()


def set_window_title(title):
    os.system(f"title {title}")


def find_window(title, timeout=3):
    """Find window by title within a given timeout."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        window = gw.getWindowsWithTitle(title)
        if window:
            return window[0]
        time.sleep(0.1)
    logging.debug(f"Window '{title}' not found within timeout.")
    return None


def assign_slot_and_name_window(window_type: WindowType, window_name: str):
    """Assign a slot and sets window title based on window type."""
    if window_type in (WindowType.ACCEPTED_SCRIPT, WindowType.DENIED_SCRIPT):
        if window_type == WindowType.DENIED_SCRIPT:
            db_handler = denied_sdh
        else:
            db_handler = sdh
        slot_assigned = db_handler.occupy_first_free_slot()

        if slot_assigned is None:
            logging.error(
                f"No slot available for window type: {window_type}")
            return None, None

        if window_type == WindowType.DENIED_SCRIPT:
            title = f"{window_name} - denied ({slot_assigned})"
        else:
            title = window_name
        set_window_title(title)
        db_handler.set_slot_main_name(slot_assigned, title)
        return slot_assigned, title

    elif window_type is WindowType.SERVER:
        title = SERVER_WINDOW_NAME
        set_window_title(title)
        return None, title


def calculate_main_window_properties(window_type: WindowType, slot: int):
    """Calculates window size and position based on slot and type."""
    if window_type in (WindowType.ACCEPTED_SCRIPT, WindowType.DENIED_SCRIPT):

        if window_type == WindowType.ACCEPTED_SCRIPT:
            width = MAIN_WINDOW_WIDTH
            height = MAIN_WINDOW_HEIGHT
            x_pos = -width * (1 + slot // MAX_WINDOWS_PER_COLUMN)
            y_pos = height * (slot % MAX_WINDOWS_PER_COLUMN)
            return width, height, x_pos, y_pos
        elif window_type == window_type.DENIED_SCRIPT:
            width = MAIN_WINDOW_WIDTH
            height = 200
            x_pos = -1920 + width * (slot // 5)
            y_pos = height * (slot % 5)  # fit 5 terminals
            return width, height, x_pos, y_pos

    elif window_type is window_type.SERVER:
        width = 700
        height = 400
        x_pos = -1920
        y_pos = 640
        return width, height, x_pos, y_pos

    return None


def calculate_secondary_window_properties(
        slot, secondary_windows: list[sw.SecondaryWindow])\
        -> list[tuple[int, int, int, int]]:
    """Set properties for a list of secondary window """
    properties = []
    x_pos_offset = 0

    for i in range(0, len(secondary_windows)):
        width = secondary_windows[i].width
        height = secondary_windows[i].height
        x_pos = ((-MAIN_WINDOW_WIDTH * (1 + slot // MAX_WINDOWS_PER_COLUMN)
                  + x_pos_offset))
        y_pos = MAIN_WINDOW_HEIGHT * (slot % MAX_WINDOWS_PER_COLUMN)

        properties.append = width, height, x_pos, y_pos
        x_pos_offset -= width  # to avoid overlap

    return properties


def adjust_window(window: gw.Win32Window,
                  properties: tuple[int, int, int, int],
                  resize=True, move=True):
    """Adjust window position and size."""
    if window:
        if resize:
            window.resizeTo(*properties[:2])
        if move:
            window.moveTo(*properties[2:])
    else:
        logging.error("Window not found for adjusting position.")


def get_all_windows_names():
    names = sdh.get_all_names()
    names.append(SERVER_WINDOW_NAME)
    return names


def set_windows_to_topmost():
    """Set the scripts windows to be on top of the screen."""
    windows_names = get_all_windows_names()
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


def manage_main_window(window_type, window_name, secondary_windows_names=None):
    """Manage window allocation and positioning."""
    slot, title = assign_slot_and_name_window(window_type, window_name)
    if slot is None:
        return

    properties = calculate_main_window_properties(window_type, slot)
    window = find_window(title)
    window.restore()
    adjust_window(window, properties)

    if secondary_windows_names:
        sdh.set_slot_secondary_names(slot, secondary_windows_names)


def manage_secondary_windows(
        slot, secondary_windows: list[sw.SecondaryWindow]):
    """Fit secondary windows next to main one"""
    properties = calculate_secondary_window_properties(slot, secondary_windows)
    for i in range(0, len(secondary_windows)):
        adjust_window(secondary_windows[i].name, properties[i])


if __name__ == '__main__':
    logging.info("Window Manager Script Started")
    # Example usage
    manage_main_window(WindowType.ACCEPTED_SCRIPT, "Example Script")

"""
Module used to transform the terminal windows of running scripts so that they
fit my screen nicely on my second monitor, in accordance with the amount of
windows already present.
"""
import logging
import os
import time
from enum import Enum, auto

import pygetwindow as gw
import win32con
import win32gui

import denied_slots_db_handler as denied_sdh
import slots_db_handler as sdh

MAIN_WINDOW_WIDTH = 600
MAIN_WINDOW_HEIGHT = 260  # 1040/4 = 260 (40px is for bottom Windows menu)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename="temp/logs/twm_v3.log",
    filemode="w")

logger = logging.getLogger(__name__)


class WindowType(Enum):
    DENIED_SCRIPT = auto()
    ACCEPTED_SCRIPT = auto()
    SERVER = auto()


def assign_slot_and_name_window(window_type: WindowType,
                                window_name: str) -> (int | None, str):
    """Assign a slot number in the database to the terminal window that just
    spawned and assign a main name to it."""
    if window_type == WindowType.ACCEPTED_SCRIPT:
        try:
            slot_assigned = sdh.occupy_first_free_slot()
            if slot_assigned is None:
                raise ValueError

            title = window_name
            os.system(f"title {title}")
            sdh.name_slot(slot_assigned, title)
            return slot_assigned, title
        except ValueError as e:
            print(e)

    elif window_type == WindowType.DENIED_SCRIPT:
        try:
            slot_assigned = denied_sdh.occupy_first_free_slot()
            if slot_assigned is None:
                raise ValueError

            title = f"{window_name} - denied ({slot_assigned})"
            os.system(f"title {title}")
            return slot_assigned, title
        except ValueError as e:
            print(e)


def join_secondaries_to_main_window(slot: int,
                                    secondary_windows: list[str]):
    """
    Adjust the positions of the secondary terminal windows who spawn from
    the main script, so that they can fit together on the screen.

    :param slot: The slot attributed to the main terminal window in the
        database.
    :param secondary_windows: List of the secondary window names.
    """
    for i in range(0, len(secondary_windows)):
        if secondary_windows[i] is not None:
            # Set windows to fixed size, might change in the future
            width = 100
            height = 100
            # Position the secondary windows on top of the main window, from
            # right to left.
            x_pos = (-MAIN_WINDOW_WIDTH * (1 + slot // 4)) + (3 - i) * 150
            y_pos = MAIN_WINDOW_HEIGHT * (slot % 4)
            properties = (width, height, x_pos, y_pos)
            restore_resize_and_move_window(secondary_windows[i], properties)


def calculate_new_window_properties(
        window_type: WindowType,
        slot_number: int) -> tuple[int, int, int, int]:
    """Calculate the size and positions for the main terminal window of the
    scripts"""
    if window_type == WindowType.ACCEPTED_SCRIPT:
        width = MAIN_WINDOW_WIDTH
        height = MAIN_WINDOW_HEIGHT
        x_pos = -width * (1 + slot_number // 4)
        y_pos = height * (slot_number % 4)

        return width, height, x_pos, y_pos

    elif window_type == WindowType.DENIED_SCRIPT:
        width = 600
        height = 200
        x_pos = -1920 + width * (slot_number // 5)
        y_pos = height * (slot_number % 5)

        return width, height, x_pos, y_pos


def restore_resize_and_move_window(
        window_title: str,
        new_properties: tuple[int, int, int, int],
        resize: bool = True,
        move: bool = True):
    """
    Restore, revealing it from its potential minimized state, then reposition
    and/or and transform a window.

    :param window_title: name of the window
    :param new_properties: in order: new_width, new_height, new_x, new_y
    :param move: do you want to reposition ?
    :param resize: do you want to resize ?
    """
    new_width, new_height, new_x, new_y = new_properties

    timeout = 3
    start_time = time.time()
    tries = 0

    # Poll for the window: if it has been renamed recently it might need a
    # bit of time to be found after the name update (done asynchronously
    # with the os.system module).
    while True:
        if time.time() - start_time > timeout:
            print("Window Search timed out.")
            break

        window = gw.getWindowsWithTitle(window_title)
        if window:
            print(f"Window '{window_title} found")
            window = window[0]
            window.restore()  # We start all the scripts as subprocesses
            # minimized
            if resize:
                window.resizeTo(new_width, new_height)
            if move:
                window.moveTo(new_x, new_y)
            break
        else:
            tries += 1
            if time.time() - start_time > 0.5 or tries == 1:
                logging.debug(
                    f"Window '{window_title}' not found. trying again."
                    f"Tries = {tries}")


def set_windows_to_topmost():
    """Set all the windows of the running scripts to be on top of the
    screen."""
    windows_names_list = sdh.get_all_names()
    windows_names_list.append("SERVER")

    windows_names_list.reverse()
    # We reverse the order of the list in order to have the secondary windows
    # displayed  over the main window when set to "TOPMOST" (the first
    # windows passed to SetWindowPos get "TOPMOST" priority). Actually, IDK.
    # But, for now, it works pretty well like that.

    for name in windows_names_list:
        window = win32gui.FindWindow(None, name)
        if window:
            win32gui.SetWindowPos(window,
                                  win32con.HWND_TOPMOST,
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


def unset_windows_to_topmost():
    """Set the scripts windows fore/background behavior back to normal."""
    windows_names_list = sdh.get_all_names()
    windows_names_list.append("SERVER")

    for name in windows_names_list:
        window = win32gui.FindWindow(None, name)
        if window:
            win32gui.SetWindowPos(window,
                                  win32con.HWND_NOTOPMOST,
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


def restore_all_windows():
    """Show all the scripts windows who have been minimized"""
    windows_names_list = sdh.get_all_names()
    windows_names_list.append("SERVER")

    for window in windows_names_list:
        window = gw.getWindowsWithTitle(window)
        if window:
            window = window[0]
            window.restore()


def close_window(slot: int):
    # Free up the occupied database slot
    sdh.free_slot(slot)


def get_all_windows_titles():
    print(gw.getAllTitles())


def adjust_window(window_type: WindowType, window_name: str,
                  secondary_windows: list[str] = None) -> int:
    """
    Adjust the terminal window's and its potential secondary windows' sizes and
    positions.
    :param window_type: decides, in order to adjust accordingly, which the
        recently spawned terminal window is of the following:
        1. A denied script that will soon exit automatically.
        2. An accepted script that will give continuous feedback.
        3. The server script.
    :param window_name: name of the main window to adjust.
    :param secondary_windows: list of the secondary window to adjust.
    """

    if window_type == WindowType.DENIED_SCRIPT:
        slot, title = assign_slot_and_name_window(window_type, window_name)
        properties = calculate_new_window_properties(window_type, slot)
        restore_resize_and_move_window(title, properties)
        return slot

    elif window_type == WindowType.ACCEPTED_SCRIPT:
        slot, title = assign_slot_and_name_window(window_type, window_name)
        properties = calculate_new_window_properties(window_type, slot)
        restore_resize_and_move_window(title, properties)
        if secondary_windows:
            sdh.insert_secondary_names(slot, secondary_windows)
            # Note: the secondary windows positions cannot be adjusted at the
            # script launch, since they usually appear later, after some script
            # logic has been executed. We will adjust their position by
            # calling the "join_secondaries" function later on.
        return slot

    elif window_type == WindowType.SERVER:
        os.system(f"title SERVER")  # make sure the SERVER cmd prompt is,
        # in fact, named "SERVER"
        time.sleep(0.2)  # give time to windows for renaming the cmd
        server_window = win32gui.FindWindow(None, "SERVER")
        if server_window:
            win32gui.SetWindowPos(server_window, None, -1920, 640, 700, 400, 0)


def readjust_windows():
    """Look if they are free slots available in the database before the ones
    currently occupied. E.g. slot 7 is occupied while slot 3 is free. If there
    are, shift the currently occupied slots to the earlier free ones. Then,
    adjust the windows properties in accordance with their new designated
    slot."""
    free_slots = sdh.get_all_free_slots()
    occupied_slots = sdh.get_all_occupied_slots()
    occupied_slots.reverse()  # we want to match the highest occupied slot
    # with the lowest free slot
    if free_slots:
        for i in range(0, len(free_slots)):
            if occupied_slots[i] > free_slots[i]:
                old_slot = occupied_slots[i]
                new_slot = free_slots[i]
                print(f"{new_slot} is free while {old_slot} is occupied, "
                      f"swapping")

                names = sdh.get_full_names(old_slot)
                main_name = names[0]
                sdh.occupy_slot(new_slot, names)
                sdh.free_slot(old_slot)

                hwnd = win32gui.FindWindow(None, main_name)
                if hwnd:
                    properties = calculate_new_window_properties(
                        WindowType.ACCEPTED_SCRIPT, new_slot)
                    restore_resize_and_move_window(main_name, properties)
                    join_secondaries_to_main_window(new_slot, names[1:])
                else:
                    print(f"no window with title '{main_name}' found.")

            else:
                print(f"slot {free_slots[i]} is free but comes later than "
                      f"latest occupied slot {occupied_slots[i]} ")
                break
    else:
        print('no free slots found')


def main():
    slot, title = assign_slot_and_name_window(
        WindowType.ACCEPTED_SCRIPT, "test")
    properties = calculate_new_window_properties(
        WindowType.ACCEPTED_SCRIPT, slot)
    restore_resize_and_move_window(title, properties)
    input("press enter to close and free the slot")
    close_window(slot)


if __name__ == '__main__':
    readjust_windows()

"""
Module used to transform the terminal windows of running scripts so that they
fit my screen nicely on my second monitor, in accordance with the amount of
windows already present
"""

import time
import pygetwindow as gw
import os
import slots_db_handler
import win32gui
import win32con
from enum import Enum, auto


class WindowType(Enum):
    DENIED_SCRIPT = auto()
    RUNNING_SCRIPT = auto()
    SERVER = auto()


def assign_slot_and_rename_window(name: str) -> (int, str):
    """Assign a slot in the database to the cmd window that just spawned
    and rename it accordingly. Then, update the database with the new window
    name assigned to the slot"""

    # Assign a slot number to the terminal window
    slot_assigned = slots_db_handler.populate_first_free_slot()
    if slot_assigned is not None:
        # Rename the terminal window if a slot was found
        new_window_title = name + str(slot_assigned)
        os.system(f"title {new_window_title}")
        # Register that new name in the database
        slots_db_handler.name_slot(slot_assigned, new_window_title)
        return slot_assigned, new_window_title
    else:
        raise ValueError(f"slot assigned was {type(slot_assigned)}. "
                         f"Could not assign to a slot.")


def calculate_new_window_properties(slot_number: int) \
        -> tuple[int, int, int, int]:
    # Check that the parameter is an integer
    if not isinstance(slot_number, int):
        raise TypeError("slot_number must be of type int")

    # Use the slot number to calculate the desired new position and size
    width = 600
    height = 260
    x_pos = -600 * (1 + slot_number // 4)
    y_pos = 260 * (slot_number % 4)

    return width, height, x_pos, y_pos


def resize_and_move_window(window_title: str,
                           new_properties: tuple[int, int, int, int]):
    """
    Reposition and transform the window to: somewhere, under the rainbow... !
    :param window_title: title of the window
    :param new_properties: In order: new_width, new_height, new_x, new_y
    :return: None
    """
    new_width, new_height, new_x, new_y = new_properties

    # Set a time-out time for the loop to exist
    timeout = 3
    start_time = time.time()

    # Poll for the window recently renamed.
    while True:
        if time.time() - start_time > timeout:
            print("Window Search timed out.")
            break

        # Obtain a list with the matching title windows
        window = gw.getWindowsWithTitle(window_title)
        if window:
            window = window[0]
            window.resizeTo(new_width, new_height)
            window.moveTo(new_x, new_y)
            break
        else:
            print(f"Window "'{window_title}'" not found. trying again")
            time.sleep(0.01)  # limit the speed of the loop


def set_windows_to_topmost():
    """Set all the cmd windows of the running scripts to be topmost"""
    windows_names_list = slots_db_handler.get_all_names()
    windows_names_list.append("SERVER")
    for name in windows_names_list:
        window = win32gui.FindWindow(None, name)
        if window:
            win32gui.SetWindowPos(window,
                                  win32con.HWND_TOPMOST,
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


def unset_windows_to_topmost():
    """Set terminal windows focus behavior back to normal"""
    windows_names_list = slots_db_handler.get_all_names()
    windows_names_list.append("SERVER")
    print(gw.getAllWindows())
    print(gw.getAllTitles())

    for name in windows_names_list:
        window = win32gui.FindWindow(None, name)
        if window:
            win32gui.SetWindowPos(window,
                                  win32con.HWND_NOTOPMOST,
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


def close_window(slot):
    # Free up the occupied slot when the window is closed
    slots_db_handler.free_slot(slot)


def adjust_window(window_type: WindowType, window_name: str) -> int:
    """
    Decide which the recently spawned terminal window is of the following:

    1. A denied script that will soon exit automatically. (lock file)
    2. A running script that will give continuous feedback.
    3. The server script.

    And adjust the terminal window accordingly.
    """

    if window_type == WindowType.DENIED_SCRIPT:
        pass

    elif window_type == WindowType.RUNNING_SCRIPT:
        try:
            slot, title = assign_slot_and_rename_window(window_name)
            properties = calculate_new_window_properties(slot)
            resize_and_move_window(title, properties)
            return slot
        except ValueError as e:
            print(e)
            input('enter to quit')

    elif window_type == WindowType.SERVER:
        os.system(f"title SERVER")
        time.sleep(0.2)  # give time to windows to update cmd name
        server_window = win32gui.FindWindow(None, "SERVER")

        # set the server to be always on top, move it to a predefined
        # location, a transform it to a predefined size. (args in order:
        # x_pos, y_pos, width, height
        win32gui.SetWindowPos(server_window,
                              None,
                              -1920, 640, 700, 400,
                              0)


def main():
    slot, title = assign_slot_and_rename_window("test")
    properties = calculate_new_window_properties(slot)
    resize_and_move_window(title, properties)
    input("press enter to close and free the slot")
    close_window(slot)


if __name__ == '__main__':
    main()

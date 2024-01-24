import time
import pygetwindow as gw
import os
import re
import slots_db_handler


# transform the terminal window so that it fits my screen nicely, on a second monitor
def resize_and_move_window(window_title, new_width, new_height, new_x, new_y):
    timeout = 3
    start_time = time.time()
    while True:  # keep trying to get a window title match, cause the os takes a bit of time to rename it
        if time.time() - start_time > timeout:
            print("Window Search timed out.")
            break
        window = gw.getWindowsWithTitle(window_title)
        if window:
            window = window[0]  # in case of multiple match for the same title.
            window.resizeTo(new_width, new_height)
            window.moveTo(new_x, new_y)
            break
        else:
            print(f"Window with title '{window_title}' not found. trying again")
            time.sleep(0.01)  # so the loop doesn't go too fucking fast, but I still like it FAST.


def adjust_terminal_window():
    # assign a slot to the cmd window that just spawned and rename it accordingly.
    occupied_slot = slots_db_handler.populate_first_free_slot()
    new_window_title = "MYNAME" + str(occupied_slot)
    os.system(f"title {new_window_title}")  # "title" is the cli command that renames its window title

    # remove non digit characters to get the slot number (i.e. "2" rather than "slot2")
    slot_number = int(re.sub(r'\D', "", occupied_slot))

    # use that number to do the math used to transform the window
    width = 600
    height = 260
    x_pos = -600 * (1 + slot_number // 4)
    y_pos = 300 * (slot_number % 4)

    resize_and_move_window(new_window_title, width, height, x_pos, y_pos)

    time.sleep(0.1)

    # free up the slot when the window is closed.
    input("press enter to close and free the slot")
    slots_db_handler.free_occupied_slot(occupied_slot)
    time.sleep(0.5)


# free_all_dict_values()
slots_db_handler.free_all_occupied_slots()
# adjust_terminal_window()

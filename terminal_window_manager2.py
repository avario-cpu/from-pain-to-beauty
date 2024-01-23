import time
import json
import pygetwindow as gw
import os
import re

# read dict from JSON file
with open("terminal_window_dict.json", "r") as json_file:
    my_dict = json.load(json_file)


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
            time.sleep(0.01)


def adjust_terminal_window():
    # assign a slot to the cmd window that just spawned and rename it accordingly.
    taken_slot = get_first_free_slot_in_dict()
    print(taken_slot, "was the first open slot available")
    my_dict[taken_slot] = "MYNAME:" + str(taken_slot)
    new_window_title = my_dict[taken_slot]  # take the value of the key as a name for the window
    os.system(f"title {new_window_title}")  # renames the window with a shell command

    # transform and replace the window according to it's occupied slot number, obtained by removing non-digits char.
    slot_number = int(re.sub(r'\D', "", taken_slot))

    width = 600
    height = 300
    x_pos = -600 * (1 + slot_number // 3)
    y_pos = 300 * (slot_number % 3)

    resize_and_move_window(new_window_title, width, height, x_pos, y_pos)

    write_dict()
    time.sleep(0.1)
    input("press enter to close and free the dict entry")

    # free up the slot in the dictionary
    my_dict[taken_slot] = "FREE"
    write_dict()
    time.sleep(0.5)


def create_dict():
    # here make the dictionary, with (slot{i} : "Title") pairs
    slots = {"slot" + str(i): "FREE" for i in range(0, 9)}
    return slots


def get_first_free_slot_in_dict():
    for slot, status in my_dict.items():
        if status == "FREE":
            return slot


def write_dict():
    with open("terminal_window_dict.json", "w") as file:
        json.dump(my_dict, file)


def free_all_dict_values():
    for key in my_dict:
        my_dict[key] = "FREE"
    write_dict()


# free_all_dict_values()
adjust_terminal_window()

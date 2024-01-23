import time
import json
import pygetwindow as gw
import os


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
    width = 600
    height = 300
    x_pos = -600
    y_pos = 300

    # change the terminal window title relative to the number of windows open to allow for unique identification.
    new_window_title = f"MY TERMINAL NAME)"
    os.system(f"title {new_window_title}")

    resize_and_move_window(new_window_title, width, height, x_pos, y_pos)


# def create_dict():
#     # here make the dictionary, with (slot{i} : "Title") pairs
#     slots = {"slot" + str(i): "FREE" for i in range(1, 10)}
#     return slots


def write_dict():
    with open("terminal_window_dict.json", "w") as file:
        json.dump(my_dict, file)


with open ("terminal_window_dict.json", "r") as json_file:
    my_dict = json.load(json_file)

write_dict()

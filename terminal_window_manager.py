import time

import pygetwindow as gw
import os


# read from file how many windows are open
def get_amount_of_terminals():
    with open("cmd_windows_info/amount_of_windows.txt", "r") as file:
        terminals = int(file.read())
    print(f"amount_of_windows already displayed is: {terminals}")
    return terminals


# show the value of the variable for the number of windows detected
def print_amount_of_windows():
    with open("cmd_windows_info/amount_of_windows.txt", "r") as f:
        current_amount_of_terminals_open = int(f.read())
    print(f"current amount of windows: {current_amount_of_terminals_open}")


# raise the value written in the file by 1
def increase_amount_of_windows_by_one():
    with open("cmd_windows_info/amount_of_windows.txt", "w") as f:
        f.write(str(amount_of_terminals_open + 1))
    print_amount_of_windows()


# lower the value written in the file by 1
def lower_amount_of_windows_by_one():
    with open("cmd_windows_info/amount_of_windows.txt", "r") as f:
        last_amount = int(f.read())
    with open("cmd_windows_info/amount_of_windows.txt", "w") as f:
        f.write(str(last_amount - 1))
    print_amount_of_windows()


# this is used only for debugging purposes
def get_all_windows_name_list():
    windows = gw.getAllWindows()
    print('list of windows:\n----------------------------------------------')
    for win in windows:
        print(win.title)
    print('--------------------------------------------------------')


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
    x_pos = -600 * ((amount_of_terminals_open // 3) + 1)
    y_pos = 300 * (amount_of_terminals_open % 3)

    # change the terminal window title relative to the number of windows open to allow for unique identification.
    new_window_title = f"MY TERMINAL NAME ({amount_of_terminals_open})"
    os.system(f"title {new_window_title}")

    resize_and_move_window(new_window_title, width, height, x_pos, y_pos)
    increase_amount_of_windows_by_one()


amount_of_terminals_open = get_amount_of_terminals()

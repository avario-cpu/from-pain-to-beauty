import time

import pygetwindow as gw
import os

with open("cmd_windows_info/amount_of_windows.txt", "r") as file:
    amount_of_terminals_open = int(file.read())
print(f"amount_of_windows already displayed is: {amount_of_terminals_open}")


def increase_amount_of_windows_by_one():
    with open("cmd_windows_info/amount_of_windows.txt", "r+") as f:
        f.write(str(amount_of_terminals_open + 1))
        new_amount = f.read()

    # with open("cmd_windows_info/amount_of_windows.txt", "r") as f:

    print(f"amount_of_windows new amount: {new_amount}")


def lower_amount_of_windows_by_one():
    with open("cmd_windows_info/amount_of_windows.txt", "w") as f:
        f.write(str(amount_of_terminals_open - 1))

    with open("cmd_windows_info/amount_of_windows.txt", "r") as f:
        new_amount = int(f.read())
    print(f"amount_of_windows new amount: {new_amount}")


def get_all_windows_name_list():  # this is used only for debugging purposes
    windows = gw.getAllWindows()
    print('list of windows:\n----------------------------------------------')
    for win in windows:
        print(win.title)
    print('--------------------------------------------------------')


def resize_and_move_window(window_title, new_width, new_height, new_x, new_y):
    window = gw.getWindowsWithTitle(window_title)
    if window:
        window = window[0]  # in case of multiple title match.
        window.resizeTo(new_width, new_height)
        window.moveTo(new_x, new_y)
    else:
        print(f"Window with title '{window_title}' not found.")


def adjust_terminal_window():
    width = 600
    height = 300
    x_pos = -600 * ((amount_of_terminals_open // 3) + 1)
    y_pos = 300 * (amount_of_terminals_open % 3)

    # change the terminal window title relative to the number of windows open to allow for unique identification.
    new_terminal_title = f"MYNAME WINDOW ({amount_of_terminals_open})"
    os.system(f"title {new_terminal_title}")

    time.sleep(0.5)
    resize_and_move_window(new_terminal_title, width, height, x_pos, y_pos)
    increase_amount_of_windows_by_one()

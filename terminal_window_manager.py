import time

import pygetwindow as gw
import os

with open("cmd_windows_info/amount_of_windows.txt", "r") as file:
    amount_of_windows_displayed = int(file.read())
print(f"amount_of_windows already displayed is: {amount_of_windows_displayed}")


def reset_amount_of_windows_count():
    with open("cmd_windows_info/amount_of_windows.txt", "w") as f:
        f.write("0")


def increase_amount_of_windows_by_one():
    with open("cmd_windows_info/amount_of_windows.txt", "w") as f:
        f.write(str(amount_of_windows_displayed + 1))

    with open("cmd_windows_info/amount_of_windows.txt", "r") as f:
        new_amount = int(f.read())
    print(f"+1: amount_of_windows new amount: {new_amount}")


def lower_amount_of_windows_by_one():
    with open("cmd_windows_info/amount_of_windows.txt", "r") as f:
        last_amount = int(f.read())
    with open("cmd_windows_info/amount_of_windows.txt", "w") as f:
        f.write(str(last_amount - 1))
    with open("cmd_windows_info/amount_of_windows.txt", "r") as f:
        new_amount = int(f.read())
    print(f"-1: amount_of_windows new amount: {new_amount}")
    time.sleep(2)


def resize_and_move_window(window_title, new_width, new_height, new_x, new_y):
    windows = gw.getAllWindows()
    for win in windows:
        print(win.title)
    window = gw.getWindowsWithTitle(window_title)
    if window:
        window = window[0]  # in case of multiple title match.
        window.resizeTo(new_width, new_height)
        window.moveTo(new_x, new_y)
    else:
        print(f">>> Window with title '{window_title}' not found.")


def adjust_terminal_window_placement():
    width = 600
    height = 300
    x_pos = -600 * ((amount_of_windows_displayed // 3) + 1)
    y_pos = 300 * (amount_of_windows_displayed % 3)

    new_cmd_title = f"main.py CMD ({amount_of_windows_displayed})"
    os.system(f"title {new_cmd_title}")
    resize_and_move_window(new_cmd_title, width, height, x_pos, y_pos)
    increase_amount_of_windows_by_one()

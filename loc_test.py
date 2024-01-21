import pygetwindow as gw
import csv


def resize_and_move_window(window_title, new_width, new_height, new_x, new_y):
    window = gw.getWindowsWithTitle(window_title)
    if window:
        window = window[0]  # in case of multiple title match.
        window.resizeTo(new_width, new_height)
        window.moveTo(new_x, new_y)

        params_list = [window_title, new_width, new_height, new_x, new_y]
        with open("terminal_loc/locations.csv", mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(params_list)
    else:
        print(f"Window with title '{window_title}' not found.")


target_row_number = 2

with open("terminal_loc/locations.csv", mode='r', newline='') as file:
    csv_reader = csv.reader(file)

    for _ in range(target_row_number - 1):
        next(csv_reader)

    target_row = next(csv_reader, None)
    if target_row is not None:
        print(target_row)

    y_pos = int(target_row[4]) + 360  # move 360 pixels to the bottom (1080/3) to fit cmd size
    x_pos = int(target_row[3])
    y_size = int(target_row[2])
    x_size = int(target_row[1])

    resize_and_move_window(target_row[0], x_size, y_size, x_pos, y_pos)


import pygetwindow as gw

with open("cmd_windows_info/amount_of_windows", "r") as file:
    amount_of_windows = int(file.read())


def reset_amount_of_windows_count():
    with open("cmd_windows_info/amount_of_windows", "w") as f:
        f.write("0")


def increase_amount_of_windows_by_one():
    with open("cmd_windows_info/amount_of_windows", "w") as f:
        f.write(str(amount_of_windows + 1))


def lower_amount_of_windows_by_one():
    with open("cmd_windows_info/amount_of_windows", "w") as f:
        f.write(str(amount_of_windows - 1))


def resize_and_move_window(window_title, new_width, new_height, new_x, new_y):
    window = gw.getWindowsWithTitle(window_title)
    if window:
        window = window[0]  # in case of multiple title match.
        window.resizeTo(new_width, new_height)
        window.moveTo(new_x, new_y)
    else:
        print(f"Window with title '{window_title}' not found.")


def adjust_terminal_window_placement():
    title = "C:\WINDOWS\system32\cmd.exe - py  main.py"
    width = 600  # fixed
    height = 300
    x_pos = -600 * ((amount_of_windows // 3) + 1)
    y_pos = 300 * (amount_of_windows % 3)

    resize_and_move_window(title, width, height, x_pos, y_pos)

    increase_amount_of_windows_by_one()

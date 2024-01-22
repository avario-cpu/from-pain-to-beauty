import pygetwindow as gw
import time

print('hello')

with open("../cmd_windows_info/amount_of_windows", 'r') as f:
    content = f.read()
    numbers_of_windows = int(content)

numbers_of_windows += 1  # the window we just opened
print(f'there is/are {numbers_of_windows} window(s) displayed')

with open("../cmd_windows_info/amount_of_windows", 'r') as f:
    content = f.read()
    new_content = int(content)
    print(content)

with open("../cmd_windows_info/amount_of_windows", 'w') as f:
    new_content = new_content + 1
    f.write(str(new_content))
    print(new_content)


def define_y_pos():
    if numbers_of_windows <= 3:
        dynamic_y_pos = (numbers_of_windows - 1) * 350
        return dynamic_y_pos
    elif 3 < numbers_of_windows <= 6:
        dynamic_y_pos = (numbers_of_windows - 3) * 350
        return dynamic_y_pos


def define_x_pos():
    if numbers_of_windows <= 3:
        dynamic_x_pos = -600
        return dynamic_x_pos
    elif 3 < numbers_of_windows <= 6:
        dynamic_x_pos = -1200
        return dynamic_x_pos


def resize_and_move_window(window_title, new_width, new_height, new_x, new_y):
    window = gw.getWindowsWithTitle(window_title)
    if window:
        window = window[0]  # in case of multiple title match.
        window.resizeTo(new_width, new_height)
        window.moveTo(new_x, new_y)

    # params_list = [window_title, new_width, new_height, new_x, new_y]
    # with open("cmd_windows_info/locations.csv", mode='a', newline='') as file:
    #     csv_writer = csv.writer(file)
    #     csv_writer.writerow(params_list)
    else:
        print(f"Window with title '{window_title}' not found.")


cmd_title = "C:\WINDOWS\system32\cmd.exe"
x_size = 600
y_size = 350
x_pos = define_x_pos()
y_pos = define_y_pos()

print("x_pos:", define_x_pos())
print("y_pos:", define_y_pos())

time.sleep(2)
resize_and_move_window(cmd_title, x_size, y_size, x_pos, y_pos)

input("any key")

with open("../cmd_windows_info/amount_of_windows", 'r') as f:
    content = f.read()
    new_content = int(content)
    print(content)

with open("../cmd_windows_info/amount_of_windows", 'w') as f:
    new_content = (new_content - 1)
    f.write(str(new_content))
    print(new_content)

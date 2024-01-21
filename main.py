import time
import single_instance
import shop_scan  # this will then import client and immediately contest to websocket
import keyboard
import pygetwindow as gw
import csv


def exit_countdown():
    print('terminated.. exit in:')
    for i in range(4, 0, -1):
        print(i)
        time.sleep(1)


def initiate_scan_thread():
    if single_instance.lock_exists():
        keyboard.remove_all_hotkeys()
        exit_countdown()
        single_instance.disconnect_client()
        pass
    else:
        print("WELCOME ABROAD CAPTAIN !!!\nHOPE UR DOING WELL AND ENJOY CODING !! :D")
        time.sleep(2)
        shop_scan.scan_thread.start()
        single_instance.create_lock_file()


def stop_main():
    shop_scan.stop_detect_shop()
    keyboard.remove_all_hotkeys()
    single_instance.delete_lock()
    exit_countdown()
    single_instance.disconnect_client()


def resize_and_move_window(window_title, new_width, new_height, new_x, new_y):
    window = gw.getWindowsWithTitle(window_title)
    if window:
        window = window[0]  # in case of multiple title match.
        window.resizeTo(new_width, new_height)
        window.moveTo(new_x, new_y)
    else:
        print(f"Window with title '{window_title}' not found.")


resize_and_move_window("C:\WINDOWS\system32\cmd.exe - py  main.py ",
                       600, 360, -600, 0)
# keyboard.add_hotkey('Ctrl+Alt+Shift+F6', scan_for_shop)
keyboard.add_hotkey('Ctrl+Alt+Shift+F7', stop_main)
initiate_scan_thread()

import time

import shop_scan  # this will then import client and immediately contest to websocket
# import single_instance
import keyboard


def main():
    # single_instance.startup()
    print("Function started!")
    shop_scan.start_scan()


def print_test():
    print('test')


keyboard.add_hotkey('Ctrl+Alt+Shift+F6', main)
keyboard.add_hotkey('Ctrl+Alt+Shift+F7', shop_scan.stop_detect_shop)

try:
    while True:
        print('main running...')
        time.sleep(1)
        pass
except KeyboardInterrupt:
    # Handle KeyboardInterrupt (Ctrl+C)
    print("Program interrupted by user.")
finally:
    # Unregister the hotkey before exiting
    keyboard.remove_all_hotkeys()

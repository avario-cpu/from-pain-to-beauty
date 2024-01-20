import time

import shop_scan  # this will then import client and immediately contest to websocket
# import single_instance
import keyboard


def main():
    # single_instance.startup()
    print("Function started!")
    shop_scan.thread_shop_scan()
    # shop_scan.detect_shop()


keyboard.add_hotkey('Ctrl+Alt+Shift+P', main)
keyboard.add_hotkey('Ctrl+Alt+Shift+S', shop_scan.stop_detect_shop)

# main()
# time.sleep(5)
# shop_scan.stop_detect_shop()

import shop_scan  # this will then import client and immediately contest to websocket
# import single_instance
import keyboard

import single_instance


def scan_for_shop():
    single_instance.startup()
    shop_scan.detect_shop()
    # single_instance.exit_script()


def start_main():  # absolutely zero idea why I have to do it this way, but I fucking have to, else it starts right away
    scan_for_shop()
    print("Function started!")


# keyboard.add_hotkey('Ctrl+Alt+Shift+P', start_main())

try:
    while True:
        pass
except KeyboardInterrupt:
    # Handle KeyboardInterrupt (Ctrl+C)
    print("Program interrupted by user.")
finally:
    # Clean up or perform any necessary tasks before exiting
    keyboard.remove_all_hotkeys()

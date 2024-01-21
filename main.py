import time
import single_instance
import shop_scan  # this will then import client and immediately contest to websocket
# import single_instance
import keyboard

exit_main = False
thread_started = False


def scan_for_shop():
    if single_instance.lock_exists():
        pass
    else:
        global thread_started
        thread_started = True
        shop_scan.module_thread.start()
        print("Script Started.\n>> WELCOME ABROAD CAPTAIN !!!!!!! HOPE UR DOING WELL AND ENJOY CODING !! :D")


def stop_main():
    if thread_started:
        shop_scan.stop_detect_shop()
    single_instance.exit_script()
    global exit_main
    exit_main = True
    exit()


keyboard.add_hotkey('Ctrl+Alt+Shift+F6', scan_for_shop)
keyboard.add_hotkey('Ctrl+Alt+Shift+F7', stop_main)

try:
    while not exit_main:
        print('main running...')
        time.sleep(1)
except KeyboardInterrupt:
    # Handle KeyboardInterrupt (Ctrl+C)
    print("Program interrupted by user.")
finally:
    # Unregister the hotkey before exiting
    print("finally REACHED")
    keyboard.remove_all_hotkeys()

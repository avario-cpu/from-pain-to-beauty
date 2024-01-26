import single_instance
import shop_scanner
import time
import terminal_window_manager_v3 as twm_v3
import atexit


def exit_countdown():
    """Give a bit of time to read terminal exit statements"""
    for seconds in reversed(range(1, 10)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    pass  # "pass" is left here for debugging purposes


def main():
    window = twm_v3.adjust_window(twm_v3.WindowType.RUNNING_SCRIPT, "test")

    # If the lock file is here, don't run the script
    if single_instance.lock_exists():
        # Make sure the window is closed by the manager at exit
        atexit.register(twm_v3.close_window, window)
        # exit_countdown()
        input('enter to quit')
    else:
        # Make sure the lock file will be removed at exit
        atexit.register(single_instance.remove_lock)
        # Make sure the window is closed by the manager at exit
        atexit.register(twm_v3.close_window, window)

        # Go and run and the script !
        single_instance.create_lock_file()
        shop_scanner.start(shop_scanner.ConnectionType.WEBSOCKET)
        # exit_countdown()
        input('enter to quit')


if __name__ == "__main__":
    main()

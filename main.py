import single_instance
import shop_scanner
import time
import terminal_window_manager_v3 as twm_v3
import atexit
import threading


def exit_countdown():
    """Give a bit of time to read terminal exit statements"""
    for seconds in reversed(range(1, 10)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    pass  # "pass" is left here for debugging purposes


def main():
    # Adjust the positioning of the main script window
    window_slot = twm_v3.adjust_window(twm_v3.WindowType.ACCEPTED_SCRIPT,
                                       "test", shop_scanner.secondary_windows)

    # If the lock file is here, don't run the script
    if single_instance.lock_exists():
        atexit.register(twm_v3.close_window, window_slot)
        input('enter to quit')
    else:
        atexit.register(single_instance.remove_lock)
        atexit.register(twm_v3.close_window, window_slot)
        single_instance.create_lock_file()

        # Thread the main logic to allow for simultaneous terminal positioning
        scan_thread = threading.Thread(
            target=shop_scanner.start,
            args=(shop_scanner.ConnectionType.WEBSOCKET,))
        scan_thread.start()

        time.sleep(0.5)  # time delay to make sure the secondary window spawns

        # Adjust the positioning of the secondary window
        twm_thread = threading.Thread(
            target=twm_v3.join_secondaries_to_main_window,
            args=(window_slot, shop_scanner.secondary_windows,))
        twm_thread.start()

        twm_thread.join()
        scan_thread.join()

        input('enter to quit')


if __name__ == "__main__":
    main()

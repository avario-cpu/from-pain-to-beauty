import single_instance
import shop_scanner
import time
import terminal_window_manager_v3 as twm_v3
import atexit
import threading
import slots_db_handler as sdh


def exit_countdown():
    """Give a bit of time to read terminal exit statements"""
    for seconds in reversed(range(1, 10)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    pass  # "pass" is left here for debugging purposes


def main():
    script_name = "shop_scanner"
    # If the lock file is here, don't run the script
    if single_instance.lock_exists():
        # Adjust the positioning of the denied script window
        twm_v3.adjust_window(twm_v3.WindowType.DENIED_SCRIPT, script_name)
        input('enter to quit')
    else:
        # Adjust the positioning of the main script window
        initial_window_slot = twm_v3.adjust_window(
            twm_v3.WindowType.ACCEPTED_SCRIPT, script_name,
            shop_scanner.secondary_windows)

        atexit.register(single_instance.remove_lock)
        single_instance.create_lock_file()

        # At exit, free the slot by using the name "shop_scanner".
        atexit.register(sdh.free_slot_named, script_name)

        # Thread the main logic to allow for simultaneous terminal positioning
        scan_thread = threading.Thread(
            target=shop_scanner.start,
            args=(shop_scanner.ConnectionType.WEBSOCKET,))
        scan_thread.start()

        time.sleep(0.5)  # time delay to make sure the secondary window spawns

        # Adjust the positioning of the secondary window
        twm_thread = threading.Thread(
            target=twm_v3.join_secondaries_to_main_window,
            args=(initial_window_slot, shop_scanner.secondary_windows,))
        twm_thread.start()
        twm_thread.join()
        scan_thread.join()

        input('enter to quit')


if __name__ == "__main__":
    main()

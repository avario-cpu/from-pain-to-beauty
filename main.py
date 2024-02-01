import single_instance
import shop_watcher
import time
import terminal_window_manager_v3 as twm_v3
import atexit
import threading
import slots_db_handler as sdh
import denied_slots_db_handler as denied_sdh


def exit_countdown():
    """Give a bit of time to read terminal exit statements"""
    for seconds in reversed(range(1, 6)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    exit()


def main():
    """If there are no single instance lock file, start the Dota2 shop_watcher
     module. At launch, reposition immediately the terminal providing feedback
    regarding its execution. Shortly after, reposition the secondary window
    which the module spawns. This is all done in an asynchronous way thanks
    to a database providing information used for the window positions"""
    script_name = "dota2_shop_watcher"

    if single_instance.lock_exists():
        slot = twm_v3.adjust_window(twm_v3.WindowType.DENIED_SCRIPT,
                                    script_name)
        atexit.register(denied_sdh.free_slot, slot)
        print("\n>>> Lock file is present: exiting... <<<")
        exit_countdown()
    else:
        slot = twm_v3.adjust_window(twm_v3.WindowType.ACCEPTED_SCRIPT,
                                    script_name,
                                    shop_watcher.secondary_windows)

        single_instance.create_lock_file()
        atexit.register(single_instance.remove_lock)

        # Use the script's name to free the data entry rather than the slot ID
        atexit.register(sdh.free_slot_named, script_name)

        # Thread the main logic to allow for simultaneous terminal positioning
        watch_thread = threading.Thread(
            target=shop_watcher.start,
            args=(shop_watcher.ConnectionType.WEBSOCKET,))
        watch_thread.start()

        shop_watcher.start_event.wait()  # wait for the loop to start
        twm_v3.join_secondaries_to_main_window(slot,
                                               shop_watcher.secondary_windows)
        watch_thread.join()
        exit_countdown()


if __name__ == "__main__":
    main()


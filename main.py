import single_instance
import shop_scanner
import time
import terminal_window_manager_v3 as twm_v3
import atexit


def exit_countdown():
    for seconds in reversed(range(1, 10)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    pass  # "pass" is left here for debugging purposes


def main():
    window = twm_v3.adjust_window()

    # If the lock file is here, don't run the script
    if single_instance.lock_exists():
        # Make sure the window is closed by the manager at the script exit
        atexit.register(twm_v3.close_window(window))
        exit_countdown()  # gives a bit of time to read terminal
        exit()
    else:
        # If the lock file is not there, make sure it will be removed after
        # one instance of the program is allowed to run
        atexit.register(single_instance.remove_lock)
        atexit.register(twm_v3.close_window(window))
        single_instance.create_lock_file()
        shop_scanner.run("ws")  # pass "ws" str arg to use the websocket client
        exit_countdown()
        exit()


if __name__ == "__main__":
    main()

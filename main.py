import single_instance
import shop_scanner
import time
# import terminal_window_manager
import client


def exit_countdown():
    for seconds in reversed(range(1, 10)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    pass  # "pass" is left here for debugging purposes


def exit_procedure():
    client.disconnect()
    # terminal_window_manager.lower_amount_of_windows_by_one()
    # input("press enter")
    exit()


def main():
    # terminal_window_manager.adjust_terminal_window()

    # If the lock file is here, don't run the script.
    if single_instance.lock_exists():
        exit_countdown()  # allow for a bit of time to read terminal feedback
        exit_procedure()
    else:
        # Use the atexit library to disconnect the ws client module, and remove
        # the lock file whenever the script exits
        import atexit
        atexit.register(single_instance.remove_lock)
        atexit.register(client.disconnect)
        try:
            single_instance.create_lock_file()
            shop_scanner.run("ws")  # pass any for using websocket, or None
            # to just run without communicating with the client
            exit_procedure()  # reached once the shop_scanner loop is broken
        except KeyboardInterrupt:
            print("KeyboardInterrupt detected !")
            exit_procedure()


if __name__ == "__main__":
    main()

import single_instance
import shop_scanner
import time
import terminal_window_manager
import client


def exit_countdown():
    for seconds in reversed(range(1, 5)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)
    pass  # "pass" is left here for debugging purposes, for when I comment out the function contents.


def exit_procedure():
    terminal_window_manager.lower_amount_of_windows_by_one()
    exit_countdown()  # used to give me a bit of time in order to read a few print messages in the terminal
    client.disconnect()
    exit()


def main():
    terminal_window_manager.adjust_terminal_window()

    if single_instance.lock_exists():  # if the lock file is here, don't run the script.
        exit_procedure()
    else:
        import atexit  # makes sure we disconnect the client and remove the lock file when the script exits
        atexit.register(single_instance.remove_lock)
        atexit.register(client.disconnect)
        try:
            single_instance.create_lock_file()
            shop_scanner.scan_for_shop()
            exit_procedure()  # reached once the shop_scanner loop is broken
        except KeyboardInterrupt:
            print("KeyboardInterrupt detected !")
            exit_procedure()


if __name__ == "__main__":
    main()

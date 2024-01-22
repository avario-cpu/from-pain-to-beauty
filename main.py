import single_instance
import shop_scanner
import time
import terminal_window_manager
import client
import os


def atexit_attest():
    open("temp/atexit_attest.txt", 'x')


def exit_countdown():
    for seconds in reversed(range(1, 6)):
        print("\r" + f'cmd will close in {seconds} seconds...', end="\r")
        time.sleep(1)


def exit_procedure():
    exit_countdown()
    client.disconnect()
    terminal_window_manager.lower_amount_of_windows_by_one()


def main():
    terminal_window_manager.adjust_terminal_window_placement()
    if single_instance.lock_exists():  # if the lock file is here, don't run the script.
        exit_procedure()
    else:
        import atexit  # makes sure we disconnect and remove the lock file upon any termination of a successfully
        # started script
        atexit.register(single_instance.remove_lock)
        atexit.register(client.disconnect)
        atexit.register(atexit_attest)  # just for testing, to check it did its job. Cause I don't trust it.
        try:
            single_instance.create_lock_file()
            shop_scanner.scan_for_shop()
            exit_procedure()  # reached once the shop_scanner loop is broken
            # exit()
        except KeyboardInterrupt:
            print("KeyboardInterrupt detected !")
            exit_procedure()
            # exit()


if __name__ == "__main__":
    if os.path.isfile("temp/atexit_attest.txt"):
        os.remove("temp/atexit_attest.txt")
    main()

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


def clean_exit():
    import atexit
    atexit.register(single_instance.remove_lock)
    atexit.register(atexit_attest)
    client.disconnect()
    exit()


def main():
    terminal_window_manager.adjust_terminal_window_placement()
    if single_instance.lock_exists():
        client.disconnect()
        exit_countdown()
        terminal_window_manager.lower_amount_of_windows_by_one()
    else:
        single_instance.create_lock_file()
        shop_scanner.scan_for_shop()
        clean_exit()
        print("reached")


if __name__ == "__main__":
    if os.path.isfile("temp/atexit_attest.txt"):
        os.remove("temp/atexit_attest.txt")
    main()

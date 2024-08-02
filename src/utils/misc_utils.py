import time


def print_countdown(duration: int = 3):
    for seconds in reversed(range(1, duration)):
        print("\r" + f"Counting down from {seconds} seconds...", end="\r")
        time.sleep(1)

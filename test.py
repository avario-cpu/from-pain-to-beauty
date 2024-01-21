import threading
import time

func1_event = threading.Event()
func2_event = threading.Event()


def print_func1():
    while not func1_event.is_set():
        print("func1 running...")
        time.sleep(0.3)
    print('\nfunc1 loop stopped.\n')


def print_func2():
    while not func2_event.is_set():
        print("func 2 running...")
        time.sleep(0.3)
    print('\nfunc2 loop stopped\n')


func1 = threading.Thread(target=print_func1)
func2 = threading.Thread(target=print_func2)

func1.start()
func2.start()

time.sleep(2)

func1_event.set()
func1.join()

time.sleep(2)

func1.start()

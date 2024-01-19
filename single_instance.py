import os
import time
import client
import atexit
import main
import sys


def simulate_run():
    i = 0
    while i < 10:
        print('running script...')
        time.sleep(0.5)
        i += 1


def delete_lock():
    os.remove("temp/myapp.lock")
    print('>>>>>>>>>> removed lock <<<<<<<<<<<')


def check_for_lock():
    lock = os.path.isfile("temp/myapp.lock")
    if lock:
        print("locked into single instance, due to presence of lock file")
        # client.ws.close()  # need to close connection, because it's the first line called due to imports (from main)
        exit()
    else:
        # main.main()
        open("temp/myapp.lock", 'x')
        print(">>>>>>>>>> created lock <<<<<<<<<<<")


check_for_lock()

atexit.register(delete_lock)
# simulate_run()

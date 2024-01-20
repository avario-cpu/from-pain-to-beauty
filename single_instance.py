import os
import client


def disconnect_client():
    client.ws.close()  # necessary to close the immediate websocket connection that happens on attempt to run the script
    print(f"disconnected from websocket: {client.ws}")


def create_lock_file():  # create a lock file to prevent multiple instances of this script.
    open("temp/myapp.lock", 'x')
    print(">> created lock")


def delete_lock():  # remove lock file, done on exit, via this module exit function
    os.remove("temp/myapp.lock")
    print(">> removed lock")


def check_lock_file():
    lock = os.path.isfile("temp/myapp.lock")
    if lock:
        print("locked into single instance")
        disconnect_client()
        exit()


def rmv_terminate_file():
    terminate = os.path.isfile("temp/terminate.txt")
    if terminate:
        os.remove("temp/terminate.txt")  # allows for the "shop_scan.py" module's main loop to run again.


def startup():
    rmv_terminate_file()
    check_lock_file()
    create_lock_file()


def exit_script():  # this is the exit used upon normal termination of the script: which is basically, for now, having
    # the "shop_scan.py" module's loop broken.
    print("exiting script...")
    disconnect_client()  # disconnect from websocket.
    delete_lock()  # remove the lock file to allow for next singular script to run.
    exit()

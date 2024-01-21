import os
import client


def disconnect_client():
    client.ws.close()  # necessary to close the immediate websocket connection that happens on attempt to run the script
    print(f"disconnected from websocket: {client.ws}")


def create_lock_file():
    open("temp/myapp.lock", 'x')
    print(">> created lock")


def delete_lock():
    os.remove("temp/myapp.lock")
    print(">> removed lock")


def lock_exists():
    lock = os.path.isfile("temp/myapp.lock")
    if lock:
        print("locked file is present.")
        return True
    else:
        create_lock_file()


def exit_script():  # this is the exit used upon normal termination of the script: which is basically, for now, having
    # the "shop_scan.py" module's loop broken.
    print("exiting script... goodbye capt'n....")
    disconnect_client()  # disconnect from websocket.
    if lock_exists():
        delete_lock()  # remove the lock file to allow for next singular script to run.

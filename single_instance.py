import os
import client


def disconnect_client():
    client.ws.close()  # necessary to close the immediate websocket connection that happens on attempt to run the script
    print(f"disconnected from websocket: {client.ws}")


def create_lock_file():
    open("temp/myapp.lock", 'x')
    print("created lock file")


def delete_lock():
    os.remove("temp/myapp.lock")
    print("removed lock file")


def lock_exists():
    lock = os.path.isfile("temp/myapp.lock")
    if lock:
        print("lock file is present.")
        return True

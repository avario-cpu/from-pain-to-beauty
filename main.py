import os
import client
import shop_scan


def startup():
    rm_terminate_file()
    check_lock_file()
    create_lock_file()
    shop_scan.detect_shop()  # run main script
    exit_script()


def exit_script():  # this is the exit used upon normal termination of the script. (which is basically, for now, having
    # the "shop_scan" module's loop broken.)
    print("exiting script...")
    disconnect_client()  # disconnect from websocket.
    delete_lock()  # remove the lock file to allow for next singular script to run.
    exit()


def disconnect_client():
    client.ws.close()  # to close the established websocket connection. When main script is ran, the client
    # immediately connects, regardless of whether the rest of the scrip runs or not.
    print(f"disconnected from websocket: {client.ws}")


def create_lock_file():  # create a lock file to prevent multiple instances of this script.
    open("temp/myapp.lock", 'x')
    print(">>>>>>>>>> created lock <<<<<<<<<<<")


def delete_lock():
    os.remove("temp/myapp.lock")
    print('>>>>>>>>>> removed lock <<<<<<<<<<<')


def check_lock_file():
    lock = os.path.isfile("temp/myapp.lock")
    if lock:  # if a lock file is there, do not run script further and disconnect client.
        print("locked into single instance")
        disconnect_client()
        exit()


def rm_terminate_file():
    os.remove("temp/terminate.txt")  # allows for the shop_scan loop to run again.


startup()

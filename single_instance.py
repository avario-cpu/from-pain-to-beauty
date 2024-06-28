import os

if not os.path.exists("temp/lock_files"):
    os.makedirs("temp/lock_files")


def create_lock_file(name):
    open(f"temp/lock_files/{name}.lock", 'x')
    print("created lock file")


def remove_lock(name):
    os.remove(f"temp/lock_files/{name}.lock")
    print("removed lock file")


def lock_exists(name):
    lock = os.path.isfile(f"temp/lock_files/{name}.lock")
    if lock:
        print(f"lock file for is present for {name}")
        return True
    else:
        print(f"no lock found for {name}")
        return False

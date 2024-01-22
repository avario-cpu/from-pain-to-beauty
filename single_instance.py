import os


def create_lock_file():
    open("temp/myapp.lock", 'x')
    print("created lock file")


def remove_lock():
    os.remove("temp/myapp.lock")
    print("removed lock file")


def lock_exists():
    lock = os.path.isfile("temp/myapp.lock")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_dir_name = os.path.basename(script_dir)
    if lock:
        print(f"lock file for is present for << {script_dir_name} >>")
        return True


if not os.path.exists("temp"):  # creating the temp directory on import because it is in gitignore and will be missing
    # when checking into the repo.
    os.makedirs("temp")

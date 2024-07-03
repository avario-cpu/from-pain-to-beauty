import logging
import os
import time

from src.core import constants as const


class LockFileManager:
    def __init__(self, lock_dir: str = const.LOCK_FILES_DIR_PATH):
        self.lock_dir = lock_dir
        if not os.path.exists(self.lock_dir):
            os.makedirs(self.lock_dir)

    def create_lock_file(self, name: str):
        try:
            with open(os.path.join(self.lock_dir, f"{name}.lock"), 'x'):
                pass
            print(f"Created lock file: {name}.lock")
        except FileExistsError:
            print(f"Lock file {name}.lock already exists.")

    def remove_lock_file(self, name: str):
        try:
            os.remove(os.path.join(self.lock_dir, f"{name}.lock"))
            print(f"Removed lock file: {name}.lock")
        except FileNotFoundError:
            print(f"Lock file {name}.lock does not exist.")

    def lock_exists(self, name: str) -> bool:
        lock_path = os.path.join(self.lock_dir, f"{name}.lock")
        if os.path.isfile(lock_path):
            print(f"Lock file is present for {name}")
            return True
        else:
            print(f"No lock found for {name}")
            return False


def setup_logger(script_name: str, level: int = logging.DEBUG,
                 log_dir: str = const.LOG_DIR_PATH):
    log_file_path = os.path.join(log_dir, f'{script_name}.log')

    with open(log_file_path, 'a') as log_file:
        log_file.write('<< New Log Entry >>\n')

    logger = logging.getLogger(script_name)
    if not logger.hasHandlers():
        logger.setLevel(level)
        fh = logging.FileHandler(log_file_path)
        fh.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


def construct_script_name(file_path: str) -> str:
    """In case you forgot how this works: pass << __file__ >> as the file path
    argument from the script calling this function !"""
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    return base_name


def countdown(duration: int = 3):
    for seconds in reversed(range(1, duration)):
        print("\r" + f'Courting down from {seconds} seconds...', end="\r")
        time.sleep(1)


def main():
    setup_logger("test", 2)


if __name__ == "__main__":
    main()

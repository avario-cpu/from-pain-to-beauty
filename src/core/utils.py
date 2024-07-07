import logging
import os
import time
from logging import Logger
from typing import Optional

from src.core import constants as const

LOG_DIR = const.LOG_DIR_PATH
LOCK_DIR = const.LOCK_FILES_DIR_PATH
COMMON_LOGS = const.COMMON_LOGS_FILE_PATH


class LockFileManager:

    def __init__(self, script_name: str, logger: Optional[Logger] = None):
        self.filename = script_name  # name of script instantiating the class
        self.lock_dir = LOCK_DIR
        self.lock_file_path = os.path.join(self.lock_dir, f"{self.filename}.lock")
        self.logger = logger if logger is not None else setup_logger(SCRIPT_NAME)
        if not os.path.exists(self.lock_dir):
            os.makedirs(self.lock_dir)

    def create_lock_file(self):
        try:
            with open(self.lock_file_path, "x"):
                pass
            print(f"Created lock file: {self.filename}.lock")
        except FileExistsError:
            print(f"Lock file path: {self.lock_file_path} already exists.")

    def remove_lock_file(self):
        self.logger.debug(f"Attempting to remove lock file for" f" {self.filename}")
        try:
            os.remove(self.lock_file_path)
            print(f"Removed lock file: {self.filename}.lock")
            self.logger.debug(f"Removed lock file: {self.filename}.lock")
        except FileNotFoundError:
            print(f"Lock file path: {self.lock_file_path} does not exist.")
            self.logger.debug(f"Lock file path: {self.lock_file_path} does not exist.")

    def lock_exists(self) -> bool:
        if os.path.isfile(self.lock_file_path):
            print(f"Lock file is present for {self.filename}")
            return True
        else:
            print(f"No lock found for {self.filename}")
            return False


def construct_script_name(file_path: str) -> str:
    """In case you forgot how this works: pass << __file__ >> as the file path
    argument from the script calling this function !"""
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    return base_name


def setup_logger(script_name: str, level: int = logging.DEBUG, log_dir: str = LOG_DIR):
    script_log_file_path = os.path.join(log_dir, f"{script_name}.log")
    common_log_file_path = COMMON_LOGS

    with open(script_log_file_path, "a") as log_file:
        log_file.write("<< New Log Entry >>\n")

    logger = logging.getLogger(script_name)
    if not logger.hasHandlers():
        logger.setLevel(level)

        # Script-specific file handler
        script_fh = logging.FileHandler(script_log_file_path)
        script_fh.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(" "message)s"
        )
        script_fh.setFormatter(formatter)
        logger.addHandler(script_fh)

        # Common file handler
        common_fh = logging.FileHandler(common_log_file_path)
        common_fh.setLevel(level)
        common_formatter = logging.Formatter(
            "%(asctime)s - %(name)s:%(filename)s:%(lineno)d - %(levelname)s "
            "- %("
            "message)s"
        )
        common_fh.setFormatter(common_formatter)
        logger.addHandler(common_fh)

    return logger


def countdown(duration: int = 3):
    for seconds in reversed(range(1, duration)):
        print("\r" + f"Courting down from {seconds} seconds...", end="\r")
        time.sleep(1)


SCRIPT_NAME = construct_script_name(__file__)


def main():
    setup_logger("test", 2)


if __name__ == "__main__":
    main()

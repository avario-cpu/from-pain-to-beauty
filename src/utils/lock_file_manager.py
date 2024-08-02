import os
from logging import Logger
from typing import Optional

from src.core import constants as const
from src.utils.helpers import construct_script_name
from src.utils.logging_utils import setup_logger

LOCK_DIR = const.LOCK_FILES_DIR_PATH
SCRIPT_NAME = construct_script_name(__file__)


class LockFileManager:

    def __init__(self, script_name: str, logger: Optional[Logger] = None):
        self.filename = script_name  # name of script instantiating the class
        self.lock_dir = LOCK_DIR
        self.lock_file_path = os.path.join(self.lock_dir, f"{self.filename}.lock")
        self.logger = logger if logger is not None else setup_logger(SCRIPT_NAME)
        self.class_name = self.__class__.__name__

        if not os.path.exists(self.lock_dir):
            print(f"[{self.class_name}] Creating lock directory at {self.lock_dir}")
            os.makedirs(self.lock_dir)

    def create_lock_file(self):
        try:
            with open(self.lock_file_path, "x"):
                print(f"[{self.class_name}] Created lock file: {self.filename}.lock")
        except FileExistsError:
            print(
                f"[{self.class_name}] Lock file path: {self.lock_file_path} already exists."
            )

    def remove_lock_file(self):
        self.logger.info(f"Attempting to remove lock file for <{self.filename}>")
        try:
            os.remove(self.lock_file_path)
            print(f"[{self.class_name}] Removed lock file: {self.filename}.lock")
            self.logger.info(f"Removed lock file: {self.filename}.lock")
        except FileNotFoundError:
            print(
                f"[{self.class_name}] Lock file path: {self.lock_file_path} does not exist."
            )
            self.logger.info(f"Lock file path: {self.lock_file_path} does not exist.")

    def lock_exists(self) -> bool:
        if os.path.isfile(self.lock_file_path):
            print(f"[{self.class_name}] Lock file is present for {self.filename}")
            return True
        else:
            print(f"[{self.class_name}] No lock found for {self.filename}")
            return False

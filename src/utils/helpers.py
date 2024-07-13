import logging
import os
import time

from src.core import constants as const

LOG_DIR = const.LOG_DIR_PATH
COMMON_LOGS = const.COMMON_LOGS_FILE_PATH


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


def main():
    SCRIPT_NAME = construct_script_name(__file__)
    setup_logger(SCRIPT_NAME, 2)


if __name__ == "__main__":
    main()

import logging
import os
from logging import Logger
from typing import Literal

from src.core.constants import COMMON_LOGS_FILE_PATH, LOG_DIR_PATH

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logger(
    file_name: str,
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG",
) -> logging.Logger:
    script_log_file_path = os.path.join(LOG_DIR_PATH, f"{file_name}.log")
    common_log_file_path = COMMON_LOGS_FILE_PATH

    # Initialize the logger
    logger = logging.getLogger(file_name)
    if not logger.hasHandlers():
        logger.setLevel(LOG_LEVELS[level])

        # Script-specific file handler with UTF-8 encoding
        script_fh = logging.FileHandler(script_log_file_path, encoding="utf-8")
        script_fh.setLevel(LOG_LEVELS[level])
        formatter = logging.Formatter(
            "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
        )
        script_fh.setFormatter(formatter)
        logger.addHandler(script_fh)

        # Common file handler with UTF-8 encoding
        common_fh = logging.FileHandler(common_log_file_path, encoding="utf-8")
        common_fh.setLevel(LOG_LEVELS[level])
        common_formatter = logging.Formatter(
            "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
        )
        common_fh.setFormatter(common_formatter)
        logger.addHandler(common_fh)

    return logger


def log_empty_lines(logger: Logger, lines: int = 1):
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.stream.write(lines * "\n")
            handler.flush()


# Usage example
if __name__ == "__main__":
    logger = setup_logger("my_script", "DEBUG")
    logger.info("This is an info message.")
    log_empty_lines(logger, 2)
    logger.info("This message is after two empty lines.")

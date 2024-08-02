import logging
import os
from typing import Literal

from src.core.constants import COMMON_LOGS_FILE_PATH, LOG_DIR_PATH

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class LoggerSetup:
    def __init__(
        self,
        file_path: str,
        log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG",
    ):
        self.script_name = self.construct_script_name(file_path)
        self.log_level = LOG_LEVELS[log_level]
        self.logger = self.setup_logger()

    def construct_script_name(self, file_path: str) -> str:
        """
        Constructs a script name from the given file path. This function ensures
        that the module name is included in logging, even when the script is called
        as a subprocess, thereby avoiding the generic name '__main__' in logs.

        Args:
            file_path (str): The file path of the script. Pass the special
                             variable __file__ from the calling script to this
                             function.

        Returns:
            str: The base name of the file without the extension, suitable for use
                 as a script name in logging.
        """
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        return base_name

    def setup_logger(self) -> logging.Logger:
        script_log_file_path = os.path.join(LOG_DIR_PATH, f"{self.script_name}.log")
        common_log_file_path = COMMON_LOGS_FILE_PATH

        with open(script_log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write("<< New Log Entry >>\n")

        logger = logging.getLogger(self.script_name)
        if not logger.hasHandlers():
            logger.setLevel(self.log_level)

            # Script-specific file handler with UTF-8 encoding
            script_fh = logging.FileHandler(script_log_file_path, encoding="utf-8")
            script_fh.setLevel(self.log_level)
            formatter = logging.Formatter(
                "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
            )
            script_fh.setFormatter(formatter)
            logger.addHandler(script_fh)

            # Common file handler with UTF-8 encoding
            common_fh = logging.FileHandler(common_log_file_path, encoding="utf-8")
            common_fh.setLevel(self.log_level)
            common_formatter = logging.Formatter(
                "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s %(message)s"
            )
            common_fh.setFormatter(common_formatter)
            logger.addHandler(common_fh)

        return logger

    def log_empty_lines(self, lines: int = 1):
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.stream.write(lines * "\n")
                handler.flush()

import os
import logging


def setup_logger(script_name: str, level: int = logging.DEBUG,
                 log_dir: str = 'temp/logs'):
    log_file_path = os.path.join(log_dir, f'{script_name}.log')

    with open(log_file_path, 'a') as log_file:
        log_file.write('\n\n\n<< New Log Entry >>\n')

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


def construct_script_name(file_path: str, suffix: str) -> str:
    """
    Take the path of the calling script and returns its name with a suffix.

    In case you forgot how this works: pass << __file__ >> as the file path
    argument from the main script calling this! That's its file path.
    """
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    return suffix + base_name

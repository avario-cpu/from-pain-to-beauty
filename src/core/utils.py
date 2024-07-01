import os
import logging
import constants as const


class LockFileManager:
    def __init__(self, lock_dir="../../temp/lock_files"):
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
                 log_dir: str = '../../temp/logs'):
    if script_name[:len(const.SCRIPT_NAME_SUFFIX)] == const.SCRIPT_NAME_SUFFIX:
        script_name = script_name[len(const.SCRIPT_NAME_SUFFIX):]
        # Insane high level jutsu to remove the suffix from the script name.
        # This suffix is initially implemented to avoid having the PyCharm
        # window (with the same name as the script) be moved by the
        # terminal window manager... However, now that the log file are
        # generated according to that new name too, well, THEIR windows,
        # if they are opened get moved by my cli moving tool. So yeah...
        # that fixes it ! :)

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
    argument from the script calling this function ! That's its file path.
    """
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    return suffix + base_name


def main():
    setup_logger("test", 2)


if __name__ == "__main__":
    main()

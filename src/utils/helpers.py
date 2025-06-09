import os
import time


def print_countdown(duration: int = 3) -> None:
    """Print a countdown from the specified duration in seconds."""
    for seconds in reversed(range(1, duration)):
        print("\r" + f"Counting down from {seconds} seconds...", end="\r")
        time.sleep(1)


def construct_script_name(file_path: str) -> str:
    """Construct a script name from the given file path.

    This function ensures that the module name is included in logging, even when the
    script is called as a subprocess, thereby avoiding the generic name `__main__` in
    logs.

    Args:
        file_path (str): The file path of the script. Pass the special
                         variable `__file__` from the calling script to this
                         function.

    Returns:
        str: The base name of the file without the extension, suitable for use
             as a script name in logging.

    """
    return os.path.splitext(os.path.basename(file_path))[0]

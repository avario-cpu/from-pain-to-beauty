import argparse
import os
import subprocess

from src.config.settings import PYTHONPATH
from src.core.constants import PROJECT_DIR_PATH


def launch_main_script(clear_slots: bool = False) -> None:
    """
    Simulate the launching of an application using the terminal window manager.

    Args :
        clear_slots : Whether to clear all slots in the database before adjusting.

    """
    example_script_dir = os.path.dirname(os.path.realpath(__file__))
    example_script_filename = "example_script.py"

    clear_slots_arg = "--clear-slots" if clear_slots else ""

    command = (
        f'start cmd /k "cd /d {PROJECT_DIR_PATH}'
        f"&& set PYTHONPATH={PYTHONPATH}"
        f"&& .\\venv\\Scripts\\activate"
        f"&& cd {example_script_dir}"
        f"&& py {example_script_filename} {clear_slots_arg}"
    )

    subprocess.run(command, shell=True, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Launch the main script with an option to clear database slots."
    )
    parser.add_argument(
        "--clear-slots",
        action="store_true",
        help="Clear all slots in the database after adjusting",
    )
    args = parser.parse_args()

    launch_main_script(clear_slots=args.clear_slots)

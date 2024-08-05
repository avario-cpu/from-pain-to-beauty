import os
import subprocess

from src.config.settings import PYTHONPATH
from src.core.constants import PROJECT_DIR_PATH


def launch_main_script():
    """Simulate the launching of an application using the terminal window manager."""
    example_dir = os.path.dirname(os.path.realpath(__file__))
    example_main_script = "twm_demonstrator.py"

    command = (
        f'start cmd /k "cd /d {PROJECT_DIR_PATH}'
        f"&& set PYTHONPATH={PYTHONPATH}"
        f"&& .\\venv\\Scripts\\activate"
        f"&& cd {example_dir}"
        f"&& py {example_main_script}"
    )

    print(f"Attempting to start {example_main_script}")

    subprocess.Popen(command, shell=True)


if __name__ == "__main__":
    launch_main_script()

import os
import subprocess

from src.config.settings import PYTHONPATH
from src.core.constants import PROJECT_DIR_PATH


def launch_main_script():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    target = "twm_v4_ai_refactor.py"

    command = (
        f'start cmd /k "cd /d {PROJECT_DIR_PATH}'
        f"&& set PYTHONPATH={PYTHONPATH}"
        f"&& .\\venv\\Scripts\\activate"
        f"&& cd {script_dir}"
        f"&& py {target}"
    )

    print(f"Attempting to start {target}")

    subprocess.Popen(command, shell=True)


if __name__ == "__main__":
    launch_main_script()

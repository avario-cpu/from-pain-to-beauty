import os
from dotenv import load_dotenv

load_dotenv()

# Env file paths
PROJECT_DIR_PATH = os.getenv("PROJECT_DIR_PATH")
VENV_PATH = os.getenv("VENV_PATH")
PYTHONPATH = os.getenv("PYTHONPATH")

# General project paths
TERMINAL_WINDOW_SLOTS_DB_FILE_PATH = "src/core/terminal_window_slots.db"
APPS_DIR_PATH = "src/apps"
ROBEAU_DIR_PATH = "src/robeau"

# Temp project paths
TEMP_DIR_PATH = "temp/"
LOG_DIR_PATH = "temp/logs"
LOCK_FILES_DIR_PATH = "temp/lock_files"
COMMON_LOGS_FILE_PATH = "temp/logs/all_logs.log"

# URLs
STREAMERBOT_WS_URL = "ws://127.0.0.1:50001/"

# Window names
SERVER_WINDOW_NAME = "MY SERVER"

# Subprocesses
STOP_SUBPROCESS_MESSAGE = "stop$subprocess"  # $ character is used to avoid accidental trigger from speech to text.
SUBPROCESSES_PORTS = {
    # list of subprocesses name and their socket server ports
    "shop_watcher": 59000,
    "pregame_phase_detector": 59001,
    "robeau": 59002,
    "synonym_adder": 59003,
}

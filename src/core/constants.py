import os

from dotenv import load_dotenv

load_dotenv()
PROJECT_DIR_PATH = os.getenv('PROJECT_DIR_PATH')
VENV_PATH = os.getenv('VENV_PATH')
PYTHONPATH = os.getenv('PYTHONPATH')

SLOTS_DB_FILE_PATH = "C:\\Users\\ville\\MyMegaScript\\data\\slots.db"
SUBPROCESSES_DIR_PATH = "C:\\Users\\ville\\MyMegaScript\\src\\subprocesses"
SCRIPTS_DIR_PATH = "C:\\Users\\ville\\MyMegaScript\\src\\scripts"

TEMP_DIR_PATH = "C:\\Users\\ville\\MyMegaScript\\temp"
LOG_DIR_PATH = 'C:\\Users\\ville\\MyMegaScript\\temp\\logs'
LOCK_FILES_DIR_PATH = "C:\\Users\\ville\\MyMegaScript\\temp\\lock_files"
COMMON_LOGS_FILE_PATH = ("C:\\Users\\ville\\MyMegaScript\\temp\\logs\\all_logs"
                         ".log")

STREAMERBOT_WS_URL = "ws://127.0.0.1:50001/"

STOP_SUBPROCESS_MESSAGE = "stop subprocess"
SERVER_WINDOW_NAME = "MY SERVER"

SUBPROCESSES_PORTS = {
    # list of subprocesses name and their socket server ports
    'shop_watcher': 59000,
    'pregame_phase_detector': 59001,
    'robeau': 59002
}

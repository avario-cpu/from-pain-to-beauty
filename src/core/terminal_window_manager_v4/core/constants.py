import os

from src.config.settings import PROJECT_DIR_PATH

MAIN_WINDOW_WIDTH = 600
MAIN_WINDOW_HEIGHT = 260
MAX_WINDOWS_PER_COLUMN = 1040 // MAIN_WINDOW_HEIGHT  # So currently 4

WINDOW_NAME_SUFFIX = "twm_"
SERVER_WINDOW_NAME = "MY SERVER"
TERMINAL_WINDOW_SLOTS_DB_FILE_PATH = os.path.join(
    PROJECT_DIR_PATH, "src/core/terminal_window_manager_v4/terminal_window_slots.db"
)

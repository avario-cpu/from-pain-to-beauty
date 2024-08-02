import os

from src.core.constants import COMMON_LOGS_FILE_PATH

log_dir = os.path.dirname(COMMON_LOGS_FILE_PATH)

if not os.path.exists(log_dir):
    print(f"[src.__init__] Creating log directory at {log_dir}")
    os.makedirs(log_dir)

with open(COMMON_LOGS_FILE_PATH, "a") as log_file:
    log_file.write("<< New Log Entry >>\n")
    print(f"[src.__init__] New log entry written to {COMMON_LOGS_FILE_PATH}")

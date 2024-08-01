from src.core.constants import COMMON_LOGS_FILE_PATH
import os

print("reached src __init__")

log_dir = os.path.dirname(COMMON_LOGS_FILE_PATH)

if not os.path.exists(log_dir):
    os.makedirs(log_dir)


with open(COMMON_LOGS_FILE_PATH, "a") as log_file:
    log_file.write("<< New Log Entry >>\n")

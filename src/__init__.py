from .core.constants import COMMON_LOGS_FILE_PATH

print("reached src __init__")
with open(COMMON_LOGS_FILE_PATH, 'a') as log_file:
    log_file.write('<< New Log Entry >>\n')

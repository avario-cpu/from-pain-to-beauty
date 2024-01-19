from pathlib import Path
import os
import atexit

import shop_scan

lock = Path("lock.txt")

with open('lock.txt', 'w') as f:  # creates a lock file to allow only one instance. Error Msg is in "client" module
    f.write('This txt allows only one instance of this script, it does this by killing immediately the other instance '
            'if this file exists.')


def exit_handler():  # deletes lock file whenever the script is terminated
    os.remove("lock.txt")


if lock.is_file():  # allows only one instance of script
    print(
        'Multiple instance of script detected. Closing. Manually delete "lock.txt" file to allow for the script to run'
        'if this exit is happening by mistake')
    exit()

shop_scan.detect_shop()
atexit.register(exit_handler)

import atexit
import signal
import sys
from typing import Optional

import aiosqlite

from src.core.termwm import (
    TERMINAL_WINDOW_SLOTS_DB_FILE_PATH,
    TerminalWindowManager,
    WinType,
    slots_db_handler as sdh,
)
from src.utils.helpers import construct_script_name
from src.utils.lock_file_manager import LockFileManager
from src.utils.logging_utils import setup_logger

SCRIPT_NAME = construct_script_name(__file__)
logger = setup_logger(SCRIPT_NAME)

cleanup_functions = []


def register_atexit_func(func, *args, **kwargs):
    # Register with atexit
    atexit.register(func, *args, **kwargs)
    # Also keep track of the cleanup functions for signal handling
    cleanup_functions.append((func, args, kwargs))


def witness_atexit_execution():
    print("this print was triggered by atexit module")
    logger.debug("this log entry was triggered by atexit module")


def signal_module_cleanup():
    atexit.unregister(witness_atexit_execution)  # script will exit using signal
    for func, args, kwargs in cleanup_functions:
        try:
            print(f"called clean up func: {func.__name__}")
            logger.info(f"called clean up func: {func.__name__}")
            func(*args, **kwargs)
            atexit.unregister(func)
        except Exception as e:
            print(f"Exception during cleanup: {e}")
            logger.error(f"Exception during cleanup: {e}")


def signal_handler(sig, _):
    print(f"Signal {sig} received, calling cleanup.")
    logger.info(f"Signal {sig} received, calling cleanup.")
    signal_module_cleanup()
    sys.exit(0)


def setup_signal_handlers():
    logger.debug("Signal handlers are set up.")
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def manage_script_startup(
    slots_db_conn: aiosqlite.Connection,
    window_type: WinType,
    script_name: str,
    lock_file_manager: Optional[LockFileManager] = None,
) -> int | None:
    setup_signal_handlers()
    atexit.register(witness_atexit_execution)  # Lets us tell if cleanup
    # function were called from the atexit module, or from signal.

    terminal_window_manager = TerminalWindowManager()

    slot, name = await terminal_window_manager.adjust_window(
        slots_db_conn, window_type, script_name
    )
    if window_type == WinType.DENIED:
        register_atexit_func(sdh.free_denied_slot_sync, slot)
        print(f"\n>>> Lock file is present for {script_name} <<<")
        logger.info(f"Lock file is present for {script_name}")

    elif window_type == WinType.ACCEPTED:
        if lock_file_manager:
            lock_file_manager.create_lock_file()
            register_atexit_func(lock_file_manager.remove_lock_file)
        register_atexit_func(sdh.free_slot_by_name_sync, name)
    return slot


async def setup_script(
    script_name: str,
) -> tuple[aiosqlite.Connection | None, int | None]:
    lock_file_manager = LockFileManager(script_name)
    db_conn = await sdh.create_connection(TERMINAL_WINDOW_SLOTS_DB_FILE_PATH)

    if not db_conn:
        raise ValueError("Failed to create connection to the slots DB.")

    setup_signal_handlers()
    atexit.register(witness_atexit_execution)

    if lock_file_manager.lock_exists():
        window_type = WinType.DENIED
    else:
        window_type = WinType.ACCEPTED

    slot = await manage_script_startup(
        db_conn, window_type, script_name, lock_file_manager
    )

    return db_conn, slot

import atexit
import signal
import sys
from typing import Optional
import aiosqlite

from src.core import slots_db_handler as sdh
from src.core import terminal_window_manager_v4 as twm
from src.core.terminal_window_manager_v4 import WinType, SecondaryWindow
from src.core.utils import LockFileManager, setup_logger, construct_script_name

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
    atexit.unregister(witness_atexit_execution)  # scrip will exit using signal
    for func, args, kwargs in cleanup_functions:
        try:
            print(f"called clean up func: {func.__name__}")
            logger.info(f"called clean up func: {func.__name__}")
            func(*args, **kwargs)
            atexit.unregister(func)
        except Exception as e:
            print(f"Exception during cleanup: {e}")
            logger.error(f"Exception during cleanup: {e}")


def signal_handler(sig, _frame):
    print(f"Signal {sig} received, calling cleanup.")
    logger.info(f"Signal {sig} received, calling cleanup.")
    signal_module_cleanup()
    sys.exit(0)


def setup_signal_handlers():
    logger.debug(f"Signal handlers are set up.")
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def setup_script_basics(
    db_conn: Optional[aiosqlite.Connection],
    window_type: WinType,
    script_name: str,
    lock_file_manager: Optional[LockFileManager] = None,
    secondary_windows: Optional[list[SecondaryWindow]] = None,
) -> tuple[int | None, str]:
    """Handles task performed on most scripts launch: positioning of terminal
    window, handling of potential secondary windows, lock_file assessment,
    registering of functions called at exit"""
    setup_signal_handlers()  # Ensure signal handlers are set up
    atexit.register(witness_atexit_execution)  # Lets us tell if cleanup
    # function were called from the atexit module, or from signal.

    slot, name = await twm.manage_window(
        db_conn, window_type, script_name, secondary_windows
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
    return slot, name

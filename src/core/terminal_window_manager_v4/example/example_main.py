import asyncio
import os
import subprocess

from src.core import slots_db_handler as sdh
from src.core.constants import TERMINAL_WINDOW_SLOTS_DB_FILE_PATH
from src.core.terminal_window_manager_v4.twm_v4 import (
    MainManager,
    SecondaryWindow,
    WinType,
)


async def main(free_slots=False) -> None:
    """Simulates the main script of an application that uses the terminal window manager
    at startup.

    Args: free_slots (bool, optional): Whether to free all DB slots after adjusting.
    """

    def spawn_secondary_window(
        title: str = "Secondary Window", width: str = "200", height: str = "200"
    ) -> None:
        subprocess.Popen(["python", script_file, title, width, height])

    script_dir = os.path.dirname(os.path.realpath(__file__))
    script_file = os.path.join(script_dir, "secondary_window.py")

    conn = await sdh.create_connection(TERMINAL_WINDOW_SLOTS_DB_FILE_PATH)
    if conn:
        main_manager = MainManager()
        slot, _ = await main_manager.adjust_window(
            conn, WinType.ACCEPTED, "Example Script"
        )
        if slot is not None:
            secondary_windows = [
                SecondaryWindow(name="Secondary Window 1", width=150, height=150),
                SecondaryWindow(name="Secondary Window 2", width=150, height=150),
            ]
            for window in secondary_windows:
                spawn_secondary_window(
                    window.name, str(window.width), str(window.height)
                )

            await asyncio.sleep(1)  # Give some time for the windows to appear
            await main_manager.adjust_secondary_windows(slot, secondary_windows)

        if free_slots:
            await sdh.free_all_slots(conn)

        print("Adjusted.")
    else:
        print("Connection with DB failed to be established.")


if __name__ == "__main__":
    asyncio.run(main(free_slots=False))

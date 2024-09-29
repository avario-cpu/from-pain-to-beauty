import argparse
import asyncio
import os
import subprocess

from src.core.terminal_window_manager_v4 import (
    TERMINAL_WINDOW_SLOTS_DB_FILE_PATH,
    SecondaryWindow,
    TerminalWindowManager,
    WinType,
    slots_db_handler as sdh,
)


async def main(clear_db_slots=False) -> None:
    """
    Simulates the main script of an application that uses the terminal window manager at
    startup.

    Args: clear_db_slots: Whether to free all DB slots after adjusting.

    Usage : this script is meant to be run from the twm_demonstrator.py script and will
    simulate the cli windnow of a script being repositioned and resized.

    """

    def spawn_secondary_window(
        title: str = "Secondary Window", width: str = "200", height: str = "200"
    ) -> None:
        # pylint: disable=consider-using-with
        # (we don't want to wait for the process)
        subprocess.Popen(["python", script_file, title, width, height])

    script_dir = os.path.dirname(os.path.realpath(__file__))
    script_file = os.path.join(script_dir, "example_secondary_window.py")

    conn = await sdh.create_connection(TERMINAL_WINDOW_SLOTS_DB_FILE_PATH)

    if not conn:
        print("Connection with DB failed to be established.")
        return

    if clear_db_slots:
        await sdh.free_all_slots(conn)
        print("Freed slots.")

    main_manager = TerminalWindowManager()
    slot, _ = await main_manager.adjust_window(conn, WinType.ACCEPTED, "Example Script")

    if slot is None:
        print("No slot available/error occured.")
        return

    secondary_windows = [
        SecondaryWindow(name="Secondary Window 1", width=150, height=150),
        SecondaryWindow(name="Secondary Window 2", width=150, height=150),
    ]
    for window in secondary_windows:
        spawn_secondary_window(window.name, str(window.width), str(window.height))

    await asyncio.sleep(1)  # Give some time for the windows to appear
    await main_manager.adjust_secondary_windows(slot, secondary_windows)
    print("Adjusted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Launch the main script with an option to clear database slots."
    )
    parser.add_argument(
        "--clear-slots",
        action="store_true",
        help="Clear all slots in the database after adjusting",
    )
    args = parser.parse_args()
    print(f"Clear slots: {args.clear_slots}")
    asyncio.run(main(clear_db_slots=args.clear_slots))

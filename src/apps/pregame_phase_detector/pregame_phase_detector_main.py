import asyncio

import cv2 as cv

from src.apps.pregame_phase_detector.core.constants import (
    NEW_CAPTURE_AREA,
    SECONDARY_WINDOWS,
)
from src.apps.pregame_phase_detector.core.image_processor import ImageProcessor
from src.apps.pregame_phase_detector.core.pregame_phase_detector import (
    PreGamePhaseDetector,
)
from src.apps.pregame_phase_detector.core.shared_events import (
    mute_ssim_prints,
    secondary_windows_spawned,
)
from src.apps.pregame_phase_detector.core.socket_handler import PreGamePhaseHandler
from src.connection.websocket_client import WebSocketClient
from src.core import terminal_window_manager_v4 as twm
from src.core.constants import STREAMERBOT_WS_URL, SUBPROCESSES_PORTS
from src.core.constants import TERMINAL_WINDOW_SLOTS_DB_FILE_PATH as SLOTS_DB
from src.utils.helpers import construct_script_name, print_countdown
from src.utils.logging_utils import setup_logger
from src.utils.script_initializer import setup_script

SCRIPT_NAME = construct_script_name(__file__)
logger = setup_logger(SCRIPT_NAME, "DEBUG")

PORT = SUBPROCESSES_PORTS["pregame_phase_detector"]

# Making a test change to see if it is staged


async def setup_new_capture_area(new_capture: bool, image_processor: ImageProcessor):
    """Only used for development purposes."""
    if new_capture:
        capture_area = NEW_CAPTURE_AREA
        filename = "src/apps/pregame_phase_detector/data/opencv/new_capture.jpg"
        await image_processor.capture_new_area(capture_area, filename)


async def run_main_task(
    slot: int,
    detector: PreGamePhaseDetector,
):
    mute_ssim_prints.set()
    main_task = asyncio.create_task(detector.detect_pregame_phase())

    await secondary_windows_spawned.wait()
    await twm.manage_secondary_windows(slot, SECONDARY_WINDOWS)
    mute_ssim_prints.clear()
    await main_task
    return None


async def main():
    ws_client = None
    socket_server_task = None
    slots_db_conn = None
    try:
        slots_db_conn, slot = await setup_script(
            SCRIPT_NAME, SLOTS_DB, SECONDARY_WINDOWS
        )
        if slot is None:
            logger.error("No terminal window slot available, exiting.")
            return

        socket_server_handler = PreGamePhaseHandler(PORT, logger)
        socket_server_task = asyncio.create_task(
            socket_server_handler.run_socket_server()
        )

        ws_client = WebSocketClient(STREAMERBOT_WS_URL, logger)
        await ws_client.establish_connection()

        detector = PreGamePhaseDetector(socket_server_handler, ws_client)
        await setup_new_capture_area(False, detector.image_processor)
        await run_main_task(slot, detector)

    except Exception as e:
        print(f"Unexpected error of type: {type(e).__name__}: {e}")
        logger.exception(f"Unexpected error: {e}")
        raise

    finally:
        if socket_server_task:
            socket_server_task.cancel()
            await socket_server_task
        if ws_client:
            await ws_client.close()
        if slots_db_conn:
            await slots_db_conn.close()
        cv.destroyAllWindows()


if __name__ == "__main__":
    asyncio.run(main())
    print_countdown()

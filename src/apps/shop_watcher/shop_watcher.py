import asyncio

import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim

from src.apps.shop_watcher.core.constants import (
    SCREEN_CAPTURE_AREA,
    SECONDARY_WINDOWS,
    SHOP_TEMPLATE_IMAGE_PATH,
)
from src.apps.shop_watcher.core.shop_tracker import ShopTracker
from src.apps.shop_watcher.core.socket_handler import ShopWatcherHandler
from src.core import terminal_window_manager_v4 as twm
from src.core.constants import SUBPROCESSES_PORTS
from src.core.constants import TERMINAL_WINDOW_SLOTS_DB_FILE_PATH as SLOTS_DB
from src.utils.helpers import construct_script_name, print_countdown
from src.utils.logging_utils import setup_logger
from src.utils.script_initializer import setup_script

PORT = SUBPROCESSES_PORTS["shop_watcher"]
SCRIPT_NAME = construct_script_name(__file__)
logger = setup_logger(SCRIPT_NAME, "DEBUG")


secondary_windows_spawned = asyncio.Event()
mute_ssim_prints = asyncio.Event()


async def capture_window(area: dict[str, int]):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


async def compare_images(image_a: cv.typing.MatLike, image_b: cv.typing.MatLike):
    return ssim(image_a, image_b)


async def scan_for_shop_and_notify(
    socket_handler: ShopWatcherHandler, shop_tracker: ShopTracker
):
    template = cv.imread(SHOP_TEMPLATE_IMAGE_PATH, cv.IMREAD_GRAYSCALE)

    while not socket_handler.stop_event.is_set():
        frame = await capture_window(SCREEN_CAPTURE_AREA)
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        match_value = await compare_images(gray_frame, template)
        cv.imshow(SECONDARY_WINDOWS[0].name, gray_frame)
        secondary_windows_spawned.set()

        if cv.waitKey(1) == ord("q"):
            break
        if not mute_ssim_prints.is_set():
            print(f"SSIM: {match_value:.6f}", end="\r")

        if match_value >= 0.8:
            await shop_tracker.open_shop()

        elif match_value < 0.8:
            await shop_tracker.close_shop()
        await asyncio.sleep(0.01)


async def run_main_task(
    slot: int, socket_handler: ShopWatcherHandler, shop_tracker: ShopTracker
):
    mute_ssim_prints.set()
    main_task = asyncio.create_task(
        scan_for_shop_and_notify(socket_handler, shop_tracker)
    )

    await secondary_windows_spawned.wait()
    await twm.manage_secondary_windows(slot, SECONDARY_WINDOWS)
    mute_ssim_prints.clear()
    await main_task
    return None


async def main():
    shop_tracker = None
    try:
        slots_db_conn, slot = await setup_script(
            SCRIPT_NAME, SLOTS_DB, SECONDARY_WINDOWS
        )
        if slot is None:
            logger.error("No slot available, exiting.")
            return

        socket_server_handler = ShopWatcherHandler(PORT, logger)
        socket_server_task = asyncio.create_task(
            socket_server_handler.run_socket_server()
        )

        shop_tracker = ShopTracker(logger)
        await shop_tracker.initialize_ws_client()

        await run_main_task(slot, socket_server_handler, shop_tracker)

    except Exception as e:
        print(f"Unexpected error of type: {type(e).__name__}: {e}")
        logger.exception(f"Unexpected error: {e}")
        raise

    finally:
        if socket_server_task:
            socket_server_task.cancel()
            await socket_server_task
        if shop_tracker and shop_tracker.ws_client:
            await shop_tracker.ws_client.close()
        if slots_db_conn:
            await slots_db_conn.close()
        cv.destroyAllWindows()


if __name__ == "__main__":
    asyncio.run(main())
    print_countdown()

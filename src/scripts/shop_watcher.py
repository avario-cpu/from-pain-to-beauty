import asyncio
import logging
import random
import time
from typing import Optional
import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim
from websockets import WebSocketClientProtocol

from src.connection import socks
from src.connection import websocket
from src.core import constants as const
from src.core import slots_db_handler as sdh
from src.core import terminal_window_manager_v4 as twm
from src.core import utils
from src.core.setup import setup_script_basics
from src.core.terminal_window_manager_v4 import SecondaryWindow, WinType

SCRIPT_NAME = utils.construct_script_name(__file__)
PORT = const.SUBPROCESSES_PORTS[SCRIPT_NAME]
URL = const.STREAMERBOT_WS_URL
DB = const.SLOTS_DB_FILE_PATH

SECONDARY_WINDOWS = [SecondaryWindow("opencv_shop_scanner", 150, 100)]
SCREEN_CAPTURE_AREA = {"left": 1853, "top": 50, "width": 30, "height": 35}

SHOP_TEMPLATE_IMAGE_PATH = (
    "C:\\Users\\ville\\MyMegaScript\\data\\opencv"
    "\\shop_watch\\shop_top_right_icon.jpg"
)

logger = utils.setup_logger(SCRIPT_NAME, logging.DEBUG)
secondary_windows_spawned = asyncio.Event()
mute_ssim_prints = asyncio.Event()


class ShopTracker:
    def __init__(self):
        self.shop_is_currently_open = False
        self.shop_opening_time = None
        self.shop_open_duration_task = None
        self.flags = {"reacted_to_open_short": False, "reacted_to_open_long": False}

    async def reset_flags(self):
        for key in self.flags:
            self.flags[key] = False
        pass

    async def track_shop_open_duration(self, ws: WebSocketClientProtocol):
        while self.shop_is_currently_open:
            elapsed_time = round(time.time() - self.shop_opening_time)
            print(f"Shop has been open for {elapsed_time} seconds")

            if elapsed_time >= 5 and not self.flags["reacted_to_open_short"]:
                await react_to_shop_staying_open(ws, "short")
                self.flags["reacted_to_open_short"] = True

            if elapsed_time >= 15 and not self.flags["reacted_to_open_long"]:
                await react_to_shop_staying_open(ws, "long", elapsed_time)
                self.flags["reacted_to_open_long"] = True
            await asyncio.sleep(1)  # Adjust the sleep time as necessary

    async def open_shop(self, ws: WebSocketClientProtocol):
        if not self.shop_is_currently_open:
            self.shop_is_currently_open = True
            self.shop_opening_time = time.time()
            self.shop_open_duration_task = asyncio.create_task(
                self.track_shop_open_duration(ws)
            )
            await react_to_shop("opened", ws)

    async def close_shop(self, ws: WebSocketClientProtocol):
        if self.shop_is_currently_open:
            self.shop_is_currently_open = False
            if self.shop_open_duration_task and not self.shop_open_duration_task.done():
                self.shop_open_duration_task.cancel()
                try:
                    await self.shop_open_duration_task
                except asyncio.CancelledError:
                    print("Shop open duration tracking stopped.")
            await react_to_shop("closed", ws)
            await self.reset_flags()


class ShopWatcherHandler(socks.BaseHandler):
    """Handler for the socket server of the script. Allows for communication
    from the server to the script."""

    def __init__(self, port, script_logger):
        super().__init__(port, script_logger)
        self.stop_event = asyncio.Event()
        self.other_event = asyncio.Event()  # Demonstrative place holder

    async def handle_message(self, message: str):
        if message == const.STOP_SUBPROCESS_MESSAGE:
            self.stop_event.set()
            self.logger.info("Socket received stop message")
            print("Socket received stop message")
        elif message == "OTHER":
            self.other_event.set()
            self.logger.info("Socket received other message")
        else:
            self.logger.info(f"Socket received: {message}")
        await self.send_ack()


async def capture_window(area: dict[str, int]):
    with mss.mss() as sct:
        img = sct.grab(area)
    return np.array(img)


async def compare_images(image_a: cv.typing.MatLike, image_b: cv.typing.MatLike):
    return ssim(image_a, image_b)


async def react_to_shop(status: str, ws: WebSocketClientProtocol):
    print(f"Shop just {status}")
    if status == "opened" and ws:
        await websocket.send_json_requests(
            ws, "data/ws_requests/shop_watch/dslr_hide.json", logger
        )
    elif status == "closed" and ws:
        await websocket.send_json_requests(
            ws, "data/ws_requests/shop_watch/dslr_show.json", logger
        )
    pass


async def react_to_shop_staying_open(
    ws: WebSocketClientProtocol, duration: str, seconds: Optional[float] = None
):
    if duration == "short":
        print("rolling for a reaction to shop staying open for a short while...")
        if random.randint(1, 4) == 1:
            print("reacting !")
            await websocket.send_json_requests(
                ws, "data/ws_requests/shop_watch/brb_buying_milk_show.json", logger
            )
        else:
            print("not reacting !")
    if duration == "long":
        print("rolling for a reaction to shop staying open for a long while...")
        if random.randint(1, 3) == 1:
            print("reacting !")
            await websocket.send_json_requests(
                ws, "data/ws_requests/shop_watch/brb_buying_milk_hide.json", logger
            )
            start_time = time.time()
            while True:
                elapsed_time = (
                    time.time() - start_time + seconds if seconds is not None else 0
                )
                seconds_only = int(round(elapsed_time))
                formatted_time = f"{seconds_only:02d}"
                with open(
                    "data/streamerbot_watched/time_with_shop_open.txt", "w"
                ) as file:
                    file.write(
                        f"Bro you've been in the shop for {formatted_time} "
                        f"seconds, just buy something..."
                    )

                await asyncio.sleep(1)

        else:
            print("not reacting !")


async def scan_for_shop_and_notify(
    ws: WebSocketClientProtocol, socket_handler: ShopWatcherHandler
):
    shop_tracker = ShopTracker()
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
            await shop_tracker.open_shop(ws)

        elif match_value < 0.8:
            await shop_tracker.close_shop(ws)
        await asyncio.sleep(0.01)


async def run_main_task(
    slot: int, socket_handler: ShopWatcherHandler, ws: WebSocketClientProtocol
):
    mute_ssim_prints.set()
    main_task = asyncio.create_task(scan_for_shop_and_notify(ws, socket_handler))

    await secondary_windows_spawned.wait()
    await twm.manage_secondary_windows(slot, SECONDARY_WINDOWS)
    mute_ssim_prints.clear()
    await main_task
    return None


async def main():
    db_conn = None
    ws = None
    socket_server_task = None

    try:
        lfm = utils.LockFileManager(SCRIPT_NAME)
        db_conn = await sdh.create_connection(DB)

        if lfm.lock_exists():
            await setup_script_basics(db_conn, WinType.DENIED, SCRIPT_NAME)
        else:
            slot, name = await setup_script_basics(
                db_conn, WinType.ACCEPTED, SCRIPT_NAME, lfm, SECONDARY_WINDOWS
            )

            socket_server_handler = ShopWatcherHandler(PORT, logger)
            socket_server_task = asyncio.create_task(
                socket_server_handler.run_socket_server()
            )
            ws = await websocket.establish_ws_connection(URL, logger)
            await run_main_task(slot, socket_server_handler, ws)

    except Exception as e:
        print(f"Unexpected error of type: {type(e).__name__}: {e}")
        logger.exception(f"Unexpected error: {e}")
        raise

    finally:
        if socket_server_task:
            socket_server_task.cancel()
            await socket_server_task

        if ws:
            await ws.close()
        if db_conn:
            await db_conn.close()
        cv.destroyAllWindows()


if __name__ == "__main__":
    asyncio.run(main())
    utils.countdown()

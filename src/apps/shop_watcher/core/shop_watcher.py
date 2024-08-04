import asyncio
from logging import Logger

import cv2 as cv
import mss
import numpy as np
from skimage.metrics import structural_similarity as ssim

from src.apps.shop_watcher.core.constants import (
    SCREEN_CAPTURE_AREA,
    SECONDARY_WINDOWS,
    SHOP_TEMPLATE_IMAGE_PATH,
)
from src.apps.shop_watcher.core.shared_events import (
    mute_ssim_prints,
    secondary_windows_spawned,
)
from src.apps.shop_watcher.core.shop_tracker import ShopTracker
from src.apps.shop_watcher.core.socket_handler import ShopWatcherHandler
from src.connection.websocket_client import WebSocketClient
from src.utils.logging_utils import setup_logger

logger = setup_logger("shop_watcher", "DEBUG")


class ShopWatcher:
    def __init__(
        self,
        logger: Logger,
        socket_handler: ShopWatcherHandler,
        ws_client: WebSocketClient,
    ):
        self.secondary_windows_spawned = secondary_windows_spawned
        self.mute_ssim_prints = mute_ssim_prints
        self.socket_handler = socket_handler
        self.logger = logger
        self.shop_tracker = ShopTracker(logger, ws_client)

    @staticmethod
    async def capture_window(area: dict[str, int]):
        with mss.mss() as sct:
            img = sct.grab(area)
        return np.array(img)

    @staticmethod
    async def compare_images(image_a: cv.typing.MatLike, image_b: cv.typing.MatLike):
        return ssim(image_a, image_b)

    async def scan_for_shop_and_notify(self):
        template = cv.imread(SHOP_TEMPLATE_IMAGE_PATH, cv.IMREAD_GRAYSCALE)

        while not self.socket_handler.stop_event.is_set():
            frame = await self.capture_window(SCREEN_CAPTURE_AREA)
            gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            match_value = await self.compare_images(gray_frame, template)
            cv.imshow(SECONDARY_WINDOWS[0].name, gray_frame)
            self.secondary_windows_spawned.set()

            if cv.waitKey(1) == ord("q"):
                break
            if not self.mute_ssim_prints.is_set():
                print(f"SSIM: {match_value:.6f}", end="\r")

            if match_value >= 0.8:
                await self.shop_tracker.open_shop()
            elif match_value < 0.8:
                await self.shop_tracker.close_shop()
            await asyncio.sleep(0.01)

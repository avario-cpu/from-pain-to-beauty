"""Used to detect the shop appearing on the screen and set up further logic."""

import asyncio
from logging import Logger
from typing import cast, final

import cv2 as cv
import mss
import numpy as np
from skimage.metrics import (
    structural_similarity as ssim,  # pyright: ignore[reportUnknownVariableType]
)

from src.apps.shopwatcher.core.constants import (
    SCREEN_CAPTURE_AREA,
    SECONDARY_WINDOWS,
    SHOP_TEMPLATE_IMAGE_PATH,
)
from src.apps.shopwatcher.core.shared_events import (
    mute_ssim_prints,
    secondary_windows_spawned,
)
from src.apps.shopwatcher.core.shop_tracker import ShopTracker
from src.apps.shopwatcher.core.socket_handler import ShopWatcherHandler
from src.connection.websocket_client import WebSocketClient


@final
class ShopWatcher:
    """Detects the shop appearing on the screen and manages shop tracking logic."""

    SSIM_SIMILARITY_THRESHOLD = 0.8

    def __init__(
        self,
        socket_handler: ShopWatcherHandler,
        logger: Logger,
        ws_client: WebSocketClient,
    ) -> None:
        """Initialize the ShopWatcher class.

        Args:
            socket_handler: Handler for WebSocket connections.
            logger: Logger instance for logging, forwarded to ShopTracker.
            ws_client: Client for WebSocket communication, forwarded to ShopTracker.

        """
        self.secondary_windows_spawned = secondary_windows_spawned
        self.mute_ssim_prints = mute_ssim_prints
        self.socket_handler = socket_handler
        self.logger = logger
        self.shop_tracker = ShopTracker(logger, ws_client)

    @staticmethod
    async def _capture_window(area: dict[str, int]) -> np.ndarray:
        with mss.mss() as sct:
            img = sct.grab(area)
        return np.array(img)

    @staticmethod
    async def _compare_images(
        image_a: cv.typing.MatLike, image_b: cv.typing.MatLike
    ) -> float:
        return cast("float", ssim(image_a, image_b))

    async def scan_for_shop_and_notify(self) -> None:
        """Scan for the shop on the screen and react when it appears/disappears."""
        template = cv.imread(SHOP_TEMPLATE_IMAGE_PATH, cv.IMREAD_GRAYSCALE)

        while not self.socket_handler.stop_event.is_set():
            frame = await self._capture_window(SCREEN_CAPTURE_AREA)
            gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            match_value = await self._compare_images(gray_frame, template)
            cv.imshow(SECONDARY_WINDOWS[0].name, gray_frame)
            self.secondary_windows_spawned.set()

            if cv.waitKey(1) == ord("q"):
                break
            if not self.mute_ssim_prints.is_set():
                print(f"SSIM: {match_value:.6f}", end="\r")

            if match_value >= self.SSIM_SIMILARITY_THRESHOLD:
                await self.shop_tracker.open_shop()
            elif match_value < self.SSIM_SIMILARITY_THRESHOLD:
                await self.shop_tracker.close_shop()
            await asyncio.sleep(0.01)

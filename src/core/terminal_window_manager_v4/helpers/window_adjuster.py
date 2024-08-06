import asyncio
import os
import time
from logging import Logger
from typing import Optional

import pygetwindow  # type: ignore


class WindowAdjuster:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger

    async def find_window(
        self, title: str, timeout: int = 2
    ) -> Optional[pygetwindow.Win32Window]:
        start_time = time.time()
        duration = 0.0
        while duration < timeout:
            window = pygetwindow.getWindowsWithTitle(title)
            if window:
                return window[0]
            await asyncio.sleep(0.01)
            duration = time.time() - start_time
        self.logger.warning(f"Window <{title}> not found within {timeout}s.")
        return None

    async def adjust_window(
        self,
        title: str,
        properties: tuple[int, int, int, int],
        resize: bool = True,
        move: bool = True,
    ) -> None:
        window = await self.find_window(title)
        if window:
            window.restore()
            if resize:
                window.resizeTo(properties[0], properties[1])
            if move:
                window.moveTo(properties[2], properties[3])
            self.logger.info(f"Window <{title}> adjusted successfully.")
        else:
            self.logger.error(f"Was not able to adjust window {title}.")

    def set_window_title(self, title: str) -> None:
        os.system(f"title {title}")
        self.logger.info(f"Window title set to <{title}>.")

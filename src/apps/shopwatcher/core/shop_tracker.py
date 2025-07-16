"""Conduct logic around the shop opening and closing times."""

import asyncio
import random
import time
from logging import Logger
from typing import final

import aiofiles

from src.apps.shopwatcher.core.constants import (
    BRB_BUYING_MILK_HIDE,
    BRB_BUYING_MILK_SHOW,
    DISPLAY_TIME_SINCE_SHOP_OPENED,
    DSLR_HIDE,
    DSLR_SHOW,
    TIME_SINCE_SHOP_OPENED_TXT,
)
from src.connection.websocket_client import WebSocketClient


@final
class ShopTracker:
    """Tracks the shop's opening and closing times, and reacts accordingly."""

    SHORT_OPEN_THRESHOLD_SECONDS = 5
    LONG_OPEN_THRESHOLD_SECONDS = 15

    def __init__(self, logger: Logger, ws_client: WebSocketClient) -> None:
        """Initialize the ShopTracker with logger and websocket client.

        Args:
            logger: Logger instance for logging messages
            ws_client: WebSocket client for sending requests

        """
        self.shop_is_currently_open = False
        self.shop_opening_time = 0.0
        self.shop_open_duration_task = None
        self.flags = {
            "reacted_to_open_short": False,
            "reacted_to_open_long": False,
        }
        self.logger = logger
        self.ws = ws_client

    async def _reset_flags(self) -> None:
        for key in self.flags:
            self.flags[key] = False

    async def _track_shop_open_duration(self) -> None:
        while self.shop_is_currently_open:
            elapsed_time = round(time.time() - self.shop_opening_time)
            print(f"Shop has been open for {elapsed_time} seconds")
            if (
                elapsed_time >= self.SHORT_OPEN_THRESHOLD_SECONDS
                and not self.flags["reacted_to_open_short"]
            ):
                await self._react_to_shop_staying_open("short")
                self.flags["reacted_to_open_short"] = True

            if (
                elapsed_time >= self.LONG_OPEN_THRESHOLD_SECONDS
                and not self.flags["reacted_to_open_long"]
            ):
                await self._react_to_shop_staying_open("long", seconds=elapsed_time)
                self.flags["reacted_to_open_long"] = True
            await asyncio.sleep(1)

    async def open_shop(self) -> None:
        """Signal that the shop has opened and start tracking its duration."""
        if self.shop_is_currently_open:
            return
        self.shop_is_currently_open = True
        self.shop_opening_time = time.time()
        self.shop_open_duration_task = asyncio.create_task(
            self._track_shop_open_duration()
        )
        await self._react_to_shop("opened")

    async def close_shop(self) -> None:
        """Signal that the shop has closed and stop tracking its duration."""
        if not self.shop_is_currently_open:
            return
        self.shop_is_currently_open = False
        if self.shop_open_duration_task and not self.shop_open_duration_task.done():
            self.shop_open_duration_task.cancel()
            try:
                await self.shop_open_duration_task
            except asyncio.CancelledError:
                print("Shop open duration tracking stopped.")
        await self._react_to_shop("closed")
        await self._reset_flags()

    async def _react_to_short_shop_opening(self) -> None:
        await self.ws.send_json_requests(BRB_BUYING_MILK_SHOW)

    async def _react_to_long_shop_opening(self, seconds: float) -> None:
        await self.ws.send_json_requests(BRB_BUYING_MILK_HIDE)
        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time + seconds
            seconds_only = round(elapsed_time)
            formatted_time = f"{seconds_only:02d}"
            async with aiofiles.open(TIME_SINCE_SHOP_OPENED_TXT, "w") as file:
                await file.write(
                    f"Bro you've been in the shop for {formatted_time} seconds,"
                    " just buy something..."
                )
            await self.ws.send_json_requests(DISPLAY_TIME_SINCE_SHOP_OPENED)
            await asyncio.sleep(1)

    async def _react_to_shop_staying_open(
        self, duration: str, seconds: float | None = None
    ) -> None:
        if duration == "short":
            print("rolling for a reaction to shop staying open for a short while...")
            if random.randint(1, 4) == 1:  # noqa: S311
                print("reacting !")
                await self._react_to_short_shop_opening()
            else:
                print("not reacting !")
        elif duration == "long" and seconds:
            print("rolling for a reaction to shop staying open for a long while...")
            if random.randint(1, 3) == 1:  # noqa: S311
                print("reacting !")
                await self._react_to_long_shop_opening(seconds)
            else:
                print("not reacting !")

    async def _react_to_shop(self, status: str) -> None:
        print(f"Shop just {status}")
        if status == "opened":
            await self.ws.send_json_requests(DSLR_HIDE)
        elif status == "closed":
            await self.ws.send_json_requests(DSLR_SHOW)

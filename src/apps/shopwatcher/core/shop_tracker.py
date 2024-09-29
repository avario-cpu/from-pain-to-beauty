import asyncio
import random
import time
from logging import Logger
from typing import Optional

from src.apps.shopwatcher.core.constants import (
    BRB_BUYING_MILK_HIDE,
    BRB_BUYING_MILK_SHOW,
    DISPLAY_TIME_SINCE_SHOP_OPENED,
    DSLR_HIDE,
    DSLR_SHOW,
    TIME_SINCE_SHOP_OPENED_TXT,
)
from src.connection.websocket_client import WebSocketClient


class ShopTracker:
    def __init__(self, logger: Logger, ws_client: WebSocketClient):
        self.shop_is_currently_open = False
        self.shop_opening_time = 0.0
        self.shop_open_duration_task = None
        self.flags = {"reacted_to_open_short": False, "reacted_to_open_long": False}
        self.logger = logger
        self.ws = ws_client

    async def reset_flags(self):
        for key in self.flags:
            self.flags[key] = False

    async def track_shop_open_duration(self):
        while self.shop_is_currently_open:
            elapsed_time = round(time.time() - self.shop_opening_time)
            print(f"Shop has been open for {elapsed_time} seconds")

            if elapsed_time >= 5 and not self.flags["reacted_to_open_short"]:
                await self.react_to_shop_staying_open("short")
                self.flags["reacted_to_open_short"] = True

            if elapsed_time >= 15 and not self.flags["reacted_to_open_long"]:
                await self.react_to_shop_staying_open("long", seconds=elapsed_time)
                self.flags["reacted_to_open_long"] = True
            await asyncio.sleep(1)

    async def open_shop(self):
        if not self.shop_is_currently_open:
            self.shop_is_currently_open = True
            self.shop_opening_time = time.time()
            self.shop_open_duration_task = asyncio.create_task(
                self.track_shop_open_duration()
            )
            await self.react_to_shop("opened")

    async def close_shop(self):
        if self.shop_is_currently_open:
            self.shop_is_currently_open = False
            if self.shop_open_duration_task and not self.shop_open_duration_task.done():
                self.shop_open_duration_task.cancel()
                try:
                    await self.shop_open_duration_task
                except asyncio.CancelledError:
                    print("Shop open duration tracking stopped.")
            await self.react_to_shop("closed")
            await self.reset_flags()

    async def react_to_short_shop_opening(self):
        await self.ws.send_json_requests(BRB_BUYING_MILK_SHOW)

    async def react_to_long_shop_opening(self, seconds):
        await self.ws.send_json_requests(BRB_BUYING_MILK_HIDE)
        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time + seconds
            seconds_only = int(round(elapsed_time))
            formatted_time = f"{seconds_only:02d}"
            with open(TIME_SINCE_SHOP_OPENED_TXT, "w") as file:
                file.write(
                    f"Bro you've been in the shop for {formatted_time} seconds, just buy something..."
                )
            await self.ws.send_json_requests(DISPLAY_TIME_SINCE_SHOP_OPENED)
            await asyncio.sleep(1)

    async def react_to_shop_staying_open(
        self, duration: str, seconds: Optional[float] = None
    ):
        if duration == "short":
            print("rolling for a reaction to shop staying open for a short while...")
            if random.randint(1, 4) == 1:
                print("reacting !")
                await self.react_to_short_shop_opening()
            else:
                print("not reacting !")
        elif duration == "long":
            print("rolling for a reaction to shop staying open for a long while...")
            if random.randint(1, 3) == 1:
                print("reacting !")
                await self.react_to_long_shop_opening(seconds)
            else:
                print("not reacting !")

    async def react_to_shop(self, status: str):
        print(f"Shop just {status}")
        if status == "opened":
            await self.ws.send_json_requests(DSLR_HIDE)
        elif status == "closed":
            await self.ws.send_json_requests(DSLR_SHOW)

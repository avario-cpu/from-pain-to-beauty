import asyncio
import random
import time
from typing import Optional

from websockets import WebSocketClientProtocol

from src.connection import websocket


class ShopTracker:
    def __init__(self, logger):
        self.shop_is_currently_open = False
        self.shop_opening_time = 0.0
        self.shop_open_duration_task = None
        self.flags = {"reacted_to_open_short": False, "reacted_to_open_long": False}
        self.logger = logger

    async def reset_flags(self):
        for key in self.flags:
            self.flags[key] = False

    async def track_shop_open_duration(
        self, ws: Optional[WebSocketClientProtocol] = None
    ):
        while self.shop_is_currently_open:
            elapsed_time = round(time.time() - self.shop_opening_time)
            print(f"Shop has been open for {elapsed_time} seconds")

            if elapsed_time >= 5 and not self.flags["reacted_to_open_short"]:
                await self.react_to_shop_staying_open("short", ws=ws)
                self.flags["reacted_to_open_short"] = True

            if elapsed_time >= 15 and not self.flags["reacted_to_open_long"]:
                await self.react_to_shop_staying_open(
                    "long", ws=ws, seconds=elapsed_time
                )
                self.flags["reacted_to_open_long"] = True
            await asyncio.sleep(1)

    async def open_shop(self, ws: Optional[WebSocketClientProtocol] = None):
        if not self.shop_is_currently_open:
            self.shop_is_currently_open = True
            self.shop_opening_time = time.time()
            self.shop_open_duration_task = asyncio.create_task(
                self.track_shop_open_duration(ws)
            )
            await self.react_to_shop("opened", ws)

    async def close_shop(self, ws: Optional[WebSocketClientProtocol] = None):
        if self.shop_is_currently_open:
            self.shop_is_currently_open = False
            if self.shop_open_duration_task and not self.shop_open_duration_task.done():
                self.shop_open_duration_task.cancel()
                try:
                    await self.shop_open_duration_task
                except asyncio.CancelledError:
                    print("Shop open duration tracking stopped.")
            await self.react_to_shop("closed", ws)
            await self.reset_flags()

    async def react_to_short_shop_opening(self, ws: WebSocketClientProtocol):
        await websocket.send_json_requests(
            ws,
            "src/apps/shop_watcher/ws_requests/brb_buying_milk_show.json",
            self.logger,
        )

    async def react_to_long_shop_opening(self, ws: WebSocketClientProtocol, seconds):
        await websocket.send_json_requests(
            ws,
            "src/apps/shop_watcher/ws_requests/brb_buying_milk_hide.json",
            self.logger,
        )
        start_time = time.time()
        while True:
            elapsed_time = (
                time.time() - start_time + seconds if seconds is not None else 0
            )
            seconds_only = int(round(elapsed_time))
            formatted_time = f"{seconds_only:02d}"
            with open("data/streamerbot_watched/time_with_shop_open.txt", "w") as file:
                file.write(
                    f"Bro you've been in the shop for {formatted_time} "
                    f"seconds, just buy something..."
                )

            await asyncio.sleep(1)

    async def react_to_shop_staying_open(
        self,
        duration: str,
        seconds: Optional[float] = None,
        ws: Optional[WebSocketClientProtocol] = None,
    ):

        if duration == "short":
            print("rolling for a reaction to shop staying open for a short while...")
            if random.randint(1, 4) == 1:
                print("reacting !")
                if ws:
                    await self.react_to_short_shop_opening(ws)
            else:
                print("not reacting !")

        elif duration == "long":
            print("rolling for a reaction to shop staying open for a long while...")
            if random.randint(1, 3) == 1:
                print("reacting !")
                if ws:
                    await self.react_to_long_shop_opening(ws, seconds)
            else:
                print("not reacting !")

    async def react_to_shop(
        self, status: str, ws: Optional[WebSocketClientProtocol] = None
    ):
        print(f"Shop just {status}")
        if status == "opened" and ws:
            await websocket.send_json_requests(
                ws, "src/apps/shop_watcher/ws_requests/dslr_hide.json", self.logger
            )
        elif status == "closed" and ws:
            await websocket.send_json_requests(
                ws, "src/apps/shop_watcher/ws_requests/dslr_show.json", self.logger
            )

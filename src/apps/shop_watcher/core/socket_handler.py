import asyncio

from src.connection import socket_server
from src.core.constants import STOP_SUBPROCESS_MESSAGE


class ShopWatcherHandler(socket_server.BaseHandler):

    def __init__(self, port, script_logger):
        super().__init__(port, script_logger)
        self.stop_event = asyncio.Event()

    async def handle_message(self, message: str):
        if message == STOP_SUBPROCESS_MESSAGE:
            self.stop_event.set()
            self.logger.info("Socket received stop message")
            print("Socket received stop message")
        else:
            self.logger.info(f"Socket received: {message}")
        await self.send_ack()

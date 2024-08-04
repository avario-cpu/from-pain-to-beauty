import asyncio
from asyncio.streams import StreamReader, StreamWriter
from logging import Logger
from typing import Optional

from src.utils.helpers import construct_script_name
from src.utils.logging_utils import setup_logger

SCRIPT_NAME = construct_script_name(__file__)


class BaseHandler:

    def __init__(self, port: int, stop_message: str, logger: Optional[Logger] = None):
        self.port = port
        self.stop_message = stop_message
        self.logger = logger if logger is not None else assign_default_logger()
        self.stop_event = asyncio.Event()
        self.reader: Optional[StreamReader] = None
        self.writer: Optional[StreamWriter] = None

        if not 59000 <= port <= 59999:
            self.logger.warning(f"port {port} should rather be between 59000 and 59999")
            print("Please use a port between 59000 and 59999")

    async def handle_client(self):
        while True:
            data = await self.reader.read(1024)
            if not data:
                self.logger.info("Socket client disconnected")
                break
            message = data.decode()
            await self.handle_message(message)
        self.writer.close()
        await self.writer.wait_closed()

    async def handle_message(self, message: str):
        if message == self.stop_message:
            await self._handle_stop_message()
        else:
            await self.process_message(message)

    async def _handle_stop_message(self):
        self.stop_event.set()
        self.logger.info("Socket received stop message")
        print("Socket received stop message")
        await self.send_ack()

    async def process_message(self, _message: str):
        raise NotImplementedError(
            "process_message method must be implemented by subclasses"
        )

    async def send_ack(self):
        self.writer.write(b"ACK from Socket server")
        await self.writer.drain()

    async def handle_socket_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self.reader = reader
        self.writer = writer
        await self.handle_client()

    async def run_socket_server(self) -> None:
        self.logger.info("Starting Socket server")
        server = await asyncio.start_server(
            self.handle_socket_client, "localhost", self.port
        )
        addr = server.sockets[0].getsockname()
        self.logger.info(f"Socket server serving on {addr}")

        try:
            await server.serve_forever()
        except asyncio.CancelledError:
            self.logger.error("Socket server canceled")
        finally:
            server.close()
            await server.wait_closed()
            self.logger.info("Socket server closed")


def assign_default_logger():
    logger = setup_logger(SCRIPT_NAME, "DEBUG")
    return logger

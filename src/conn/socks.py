import asyncio
from logging import Logger

from src.core.utils import construct_script_name, setup_logger

SCRIPT_NAME = construct_script_name(__file__)


class BaseHandler:
    def __init__(self, port: int, script_logger: Logger = None):
        self.port = port
        self.logger = script_logger if script_logger is not None else (
            assign_default_logger())
        self.reader = None
        self.writer = None

        if not (59000 <= port <= 59999):
            self.logger.warning(f"{port} not between 59000 and 59999")
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
        raise NotImplementedError(
            "handle_message method must be implemented by subclasses")

    async def send_ack(self):
        self.writer.write(b"ACK from Socket server")
        await self.writer.drain()


async def handle_socket_client(reader: asyncio.StreamReader,
                               writer: asyncio.StreamWriter,
                               handler_instance: BaseHandler) -> None:
    handler_instance.reader = reader
    handler_instance.writer = writer
    await handler_instance.handle_client()


async def run_socket_server(handler_instance: BaseHandler) -> None:
    port = handler_instance.port
    logger = handler_instance.logger
    logger.info("Starting Socket server")
    server = await asyncio.start_server(
        lambda r, w: handle_socket_client(r, w, handler_instance), 'localhost',
        port)
    addr = server.sockets[0].getsockname()
    logger.info(f"Socket server serving on {addr}")

    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        logger.info("Socket server task was cancelled. Stopping server")
    finally:
        server.close()
        await server.wait_closed()
        logger.info("Socket server closed")


def assign_default_logger():
    logger = setup_logger(SCRIPT_NAME)

    return logger

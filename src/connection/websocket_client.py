from logging import Logger
from typing import Optional

import websockets
from websockets import (
    ConnectionClosedError,
    WebSocketClientProtocol,
    WebSocketException,
)

from src.utils.helpers import construct_script_name
from src.utils.logging_utils import setup_logger

SCRIPT_NAME = construct_script_name(__file__)


class WebSocketClient:
    def __init__(self, url: str, logger: Optional[Logger] = None):
        self.url = url
        self.logger = logger if logger else self.assign_default_logger()
        self.ws: Optional[WebSocketClientProtocol] = None

    async def establish_connection(self) -> Optional[WebSocketClientProtocol]:
        self.logger.info("Establishing websocket connection")
        try:
            self.ws = await websockets.connect(self.url)
            self.logger.info(f"Established websocket connection: {self.ws}")
            return self.ws
        except WebSocketException as e:
            self.logger.exception(f"Websocket Exception: {e}")
        except OSError as e:
            self.logger.error(f"Websocket error: {e}")
        return None

    async def send_json_requests(self, json_file_paths: list[str] | str):
        if isinstance(json_file_paths, str):
            json_file_paths = [json_file_paths]

        if not self.ws:
            self.logger.warning("No websocket connection established")
            return

        for json_file in json_file_paths:
            try:
                with open(json_file, "r") as file:
                    await self.ws.send(file.read())
                response = await self.ws.recv()
                if isinstance(response, bytes):
                    response = response.decode("utf-8")
                self.logger.info(f"WebSocket response: {response}")
            except ConnectionClosedError as e:
                self.logger.error(f"WebSocket connection closed: {e}")
            except WebSocketException as e:
                self.logger.error(f"WebSocket error: {e}")
            except AttributeError as e:
                self.logger.error(f"Caught exception: {e} with ws: {self.ws}")

    async def close(self):
        if self.ws:
            await self.ws.close()
            self.logger.info("WebSocket connection closed")

    @staticmethod
    def assign_default_logger() -> Logger:
        return setup_logger(SCRIPT_NAME, "DEBUG")

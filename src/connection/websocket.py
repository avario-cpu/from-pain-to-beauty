from logging import Logger
from typing import Optional

import websockets
from websockets import (
    ConnectionClosedError,
    WebSocketClientProtocol,
    WebSocketException,
)

from src.utils.logging_utils import construct_script_name, setup_logger

SCRIPT_NAME = construct_script_name(__file__)


async def establish_ws_connection(
    url: str, logger: Optional[Logger] = None
) -> WebSocketClientProtocol | None:
    logger = logger if logger is not None else assign_default_logger()
    logger.debug(f"Establishing websocket connection")
    try:
        ws = await websockets.connect(url)
        logger.info(f"Established websocket connection: {ws}")
        return ws
    except WebSocketException as e:
        logger.exception(f"Websocket Exception: {e}")
    except OSError as e:
        logger.error(f"Websocket error: {e}")
    return None


async def send_json_requests(
    ws: WebSocketClientProtocol,
    json_file_paths: str | list[str],
    logger: Optional[Logger] = None,
):
    logger = logger if logger is not None else assign_default_logger()
    if isinstance(json_file_paths, str):
        json_file_paths = [json_file_paths]
    else:
        raise TypeError(f"json_file_path must be of type 'str'")

    for json_file in json_file_paths:
        try:
            with open(json_file, "r") as file:
                await ws.send(file.read())
            response = await ws.recv()
            if isinstance(response, bytes):
                response = response.decode("utf-8")
            logger.info(f"WebSocket response: {response}")
        except ConnectionClosedError as e:
            logger.error(f"WebSocket connection closed: {e}")
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
        except AttributeError as e:
            logger.error(f"Caught exception: {e} with ws: {ws}")
        finally:
            print(f"Failed JSON request send")


def assign_default_logger():
    logger = setup_logger(SCRIPT_NAME)

    return logger

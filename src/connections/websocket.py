import websockets
from websockets import WebSocketException, ConnectionClosedError, \
    WebSocketClientProtocol
from logging import Logger


async def establish_ws_connection(url: str, logger: Logger = None) \
        -> WebSocketClientProtocol | None:
    if logger:
        logger.debug(f"Establishing websocket connection")
    try:
        ws = await websockets.connect(url)
        if logger:
            logger.info(f"Established websocket connection: {ws}")
        return ws
    except WebSocketException as e:
        if logger:
            logger.exception(f"Websocket Exception: {e}")
    except OSError as e:
        logger.error(f"Websocket error: {e}")
    return None


async def send_json_requests(ws: WebSocketClientProtocol,
                             json_file_paths: str | list[str],
                             logger: Logger = None):
    if isinstance(json_file_paths, str):
        json_file_paths = [json_file_paths]
    else:
        raise TypeError(f"must json_file_path must be of type 'str'")

    for json_file in json_file_paths:
        try:
            with open(json_file, 'r') as file:
                await ws.send(file.read())
            response = await ws.recv()
            if logger:
                logger.info(f"WebSocket response: {response}")
        except ConnectionClosedError as e:
            if logger:
                logger.exception(f"WebSocket connection closed: {e}")
        except WebSocketException as e:
            if logger:
                logger.exception(f"WebSocket error: {e}")
        except AttributeError as e:
            if logger:
                logger.exception(f"Caught exception: {e} with ws: {ws}")
        finally:
            print(f"Failed JSON request send")

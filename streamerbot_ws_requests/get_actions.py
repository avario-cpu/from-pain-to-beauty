import websockets
from websockets import WebSocketException
import asyncio
import re

WEBSOCKET_URL = "ws://127.0.0.1:8080/"


async def establish_ws_connection():
    try:
        ws = await websockets.connect(WEBSOCKET_URL)
        print(f"Established connection: {ws}")
        return ws
    except WebSocketException as e:
        print(f"Websocket error: {e}")
    except OSError as e:
        print(f"OS error: {e}")
    return None


async def send_json_request(ws, json_file_path):
    with open(json_file_path, 'r') as file:
        await ws.send(file.read())
    response = await ws.recv()
    print(f"action list: {make_pretty(response)}")


async def main():
    ws = await establish_ws_connection()
    await send_json_request(ws, "get_actions.json")


def make_pretty(msg):
    """Makes the list of actions more readable by adding new lines."""
    msg = re.sub("{", "\n{", msg)
    msg = re.sub("}],", "}],\n", msg)
    return msg


if __name__ == "__main__":
    asyncio.run(main())

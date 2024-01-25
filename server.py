"""
Websocket server made for listening to a basic StreamDeck Websocket client
plugin. This is where the scripts will be launched from... and sometimes
communicated with, although this is the kind of complex stuff I'll worry
about later.
"""

import asyncio
import websockets
from websockets import WebSocketServerProtocol
import subprocess
import os

venv_python_path = "venv/Scripts/python.exe"
print("Hi, Welcome to the server, bro. You know what to do.")

if not os.path.exists("temp"):
    os.makedirs("temp")


async def handler(websocket: WebSocketServerProtocol, path: str):
    print(f"Connection established on path: {path}")

    async for message in websocket:
        print(f"Received: message {message} on path: {path}")

        # Perform different actions based on the path
        if path == "/launcher":

            if message == "start scanner":
                if os.path.exists("temp/stop.flag"):
                    os.remove("temp/stop.flag")
                # Open the process in a new separate cmd window
                subprocess.Popen(["cmd.exe", "/c", "start",
                                  venv_python_path, "main.py"])

            elif message == "stop scanner":
                with open("temp/stop.flag", "w") as f:
                    pass

            else:
                await websocket.send(
                    "This is the /launcher path. Used to launch/exit scripts")
        else:
            await websocket.send(
                f"Unknown path: {path}. Message not recognized.")


start_server = websockets.serve(handler, "localhost", 8765)

try:
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    print('KeyboardInterrupt')

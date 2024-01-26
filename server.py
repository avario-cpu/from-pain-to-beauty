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
import terminal_window_manager_v3 as twm_v3

venv_python_path = "venv/Scripts/python.exe"


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
                print('test')

        elif path == "/windows":
            print('on windows path')
            if message == "bring to top":
                # print('reached')
                twm_v3.bring_windows_on_top()

        else:
            print(f"Unknown path: {path}.")


def main():
    print("Welcome to the server, bro. You know what to do.")

    if not os.path.exists("temp"):
        os.makedirs("temp")

    start_server = websockets.serve(handler, "localhost", 8765)

    twm_v3.adjust_window(twm_v3.WindowType.SERVER, 'SERVER')

    try:
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')


if __name__ == "__main__":
    main()

"""
Websocket server made for listening to a basic StreamDeck Websocket client
plugin. This is where the scripts will be launched from... and sometimes
communicated with, although this is the kind of complex stuff I'll worry
about later.
"""

import asyncio
import os
import re
import subprocess

import websockets
from websockets import WebSocketServerProtocol

import slots_db_handler
import terminal_window_manager_v3 as twm_v3

venv_python_path = "venv/Scripts/python.exe"


async def control_shop_watcher(message):
    if message == "start shop_watcher":
        # Open the process in a new separate cmd window: this is done to be
        # able to manipulate the position of the script's terminal with the
        # terminal window manager module.
        subprocess.Popen([
            "cmd.exe", "/c", "start", "/min", venv_python_path, "main.py"])

    elif message == "stop shop_watcher":
        with open("temp/stop.flag", "w") as f:
            pass
        await send_message_to_socket_server("Stop Subprocess")

    elif message == "remove shop_watcher lock":
        if os.path.exists("temp/myapp.lock"):
            os.remove("temp/myapp.lock")


async def operate_launcher(message):
    msg = re.search("shop_watcher", message)
    if msg is not None:
        await control_shop_watcher(message)
    else:
        print('Not a suitable launcher path message')


def manage_windows(message):
    if message == "bring to top":
        twm_v3.set_windows_to_topmost()
        twm_v3.unset_windows_to_topmost()
    elif message == "set topmost":
        twm_v3.set_windows_to_topmost()
    elif message == "unset topmost":
        twm_v3.unset_windows_to_topmost()
    elif message == "readjust":
        twm_v3.readjust_windows()
    elif message == "restore":
        twm_v3.restore_all_windows()
        pass


def manage_database(message):
    if message == "free all slots":
        slots_db_handler.free_all_occupied_slots()


async def websocket_handler(websocket: WebSocketServerProtocol, path: str):
    async for message in websocket:
        print(f"WS: Received: message '{message}' on path: {path}")

        if path == "/launcher":  # Path to start and end scripts
            await operate_launcher(message)

        elif path == "/windows":  # Path to manipulate windows properties
            manage_windows(message)

        elif path == "/database":  # Path to manipulate db entries
            manage_database(message)

        elif path == "/test":  # Path to test stuff
            if message == "get windows":
                twm_v3.get_all_windows_titles()

        else:
            print(f"Unknown path: {path}.")


async def send_message_to_socket_server(message, host='localhost', port=9999):
    reader, writer = await asyncio.open_connection(host, port)
    print(f'Sending: {message}')
    writer.write(message.encode('utf-8'))

    # Wait for the server to process the message and send a response
    data = await reader.read(1024)
    print(f'Received: {data.decode("utf-8")}')

    print('Closing the connection')
    writer.close()
    await writer.wait_closed()


async def main():
    print("Welcome to the server, bro. You know what to do.")
    if not os.path.exists("temp"):
        os.makedirs("temp")

    twm_v3.adjust_window(twm_v3.WindowType.SERVER, 'SERVER')
    websocket_server = await websockets.serve(websocket_handler, "localhost",
                                              8888)

    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    finally:
        websocket_server.close()
        await websocket_server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())

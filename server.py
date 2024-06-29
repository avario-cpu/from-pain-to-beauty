"""
Websocket server made for listening to a basic StreamDeck Websocket client
plugin. This is where the scripts will be launched from... and sometimes
communicated with, although this is the kind of complex stuff I'll worry
about later.
"""

import asyncio
import os
import subprocess

import aiosqlite
import websockets
from websockets import WebSocketServerProtocol
import constants as const
import denied_slots_db_handler as denied_sdh
import my_utils
import logging

import slots_db_handler as sdh
import terminal_window_manager_v4 as twm

SCRIPT_NAME = my_utils.construct_script_name(__file__,
                                             const.SCRIPT_NAME_SUFFIX)
logger = my_utils.setup_logger(SCRIPT_NAME, logging.DEBUG)

venv_python_path = "venv/Scripts/python.exe"
subprocess_names = list(const.SUBPROCESSES.keys())


def reset_databases(conn: aiosqlite.Connection):
    sdh.delete_table(conn)
    sdh.create_table(conn)
    sdh.initialize_slots(conn)
    denied_sdh.delete_table(conn)
    denied_sdh.create_table(conn)
    denied_sdh.initialize_slots(conn)


async def control_subprocess(instruction: str, target: str):
    if instruction == "start":
        # Open the process in a new separate cmd window: this is done to be
        # able to manipulate the position of the script's terminal with the
        # terminal window manager module.
        subprocess.Popen([
            "cmd.exe", "/c", "start", "/min", venv_python_path,
            f"{target}.py"])

    elif instruction == "stop":
        await send_message_to_subprocess_socket(
            const.STOP_SUBPROCESS_MESSAGE,
            const.SUBPROCESSES[f'{const.SCRIPT_NAME_SUFFIX + target}'])

    elif instruction == "unlock":
        if os.path.exists(f"temp/lock_files/"
                          f"{const.SCRIPT_NAME_SUFFIX + target}.lock"):
            os.remove(f"temp/lock_files/"
                      f"{const.SCRIPT_NAME_SUFFIX + target}.lock")


async def operate_launcher(message: str):
    parts = message.split()
    if len(parts) >= 2:
        instruction = parts[0]
        target = parts[1]
        if const.SCRIPT_NAME_SUFFIX + target in subprocess_names:
            await control_subprocess(instruction, target)
        else:
            print(f"Unknown target {target}")
    else:
        print("Invalid message format, must be in two parts: << instruction & "
              "target >>")


async def manage_windows(conn: aiosqlite.Connection, message: str):
    if message == "bring to top":
        await twm.bring_windows_to_foreground(conn)
    elif message == "set topmost":
        await twm.set_windows_to_topmost(conn)
    elif message == "unset topmost":
        await twm.unset_windows_to_topmost(conn)
    elif message == "readjust":
        await twm.refit_all_windows(conn)
    elif message == "restore":
        await twm.restore_all_windows(conn)
        pass


async def manage_database(conn: aiosqlite.Connection, message: str):
    if message == "free all slots":
        await sdh.free_all_slots(conn)
        await denied_sdh.free_all_slots(conn)


def create_websocket_handler(conn: aiosqlite.Connection):
    async def websocket_handler(websocket: WebSocketServerProtocol, path: str):
        async for message in websocket:
            print(f"WS Received: '{message}' on path: {path}")

            if path == "/launcher":  # Path to start and end scripts
                await operate_launcher(message)

            elif path == "/windows":  # Path to manipulate windows properties
                await manage_windows(conn, message)

            elif path == "/database":  # Path to manipulate db entries
                await manage_database(conn, message)

            elif path == "/test":  # Path to test stuff
                if message == "get windows":
                    windows_names = await twm.get_all_windows_names(conn)
                    print(windows_names)

    return websocket_handler


async def send_message_to_subprocess_socket(message: str, port: int,
                                            host='localhost'):
    """Client function to send messages to subprocesses servers"""
    reader, writer = await asyncio.open_connection(host, port)

    writer.write(message.encode('utf-8'))
    print(f'SOCK Sent: {message}')
    data = await reader.read(1024)
    print(f'SOCK Received: {data.decode("utf-8")}')

    print('Closing the connection')
    writer.close()
    await writer.wait_closed()


async def main():
    print("Welcome to the server, bro. You know what to do.")
    conn = await sdh.create_connection(const.SLOTS_DB_FILE)
    if not os.path.exists("temp"):
        os.makedirs("temp")  # just in case git remove the dir

    await twm.manage_window(conn, twm.WinType.SERVER, 'SERVER')
    websocket_server = await websockets.serve(create_websocket_handler(conn),
                                              "localhost", 50000)

    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    finally:
        websocket_server.close()
        await websocket_server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())

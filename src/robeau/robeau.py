import asyncio
import logging
import os
import random
import subprocess

from neo4j import GraphDatabase
from pydub import AudioSegment  # type: ignore
from pydub.playback import play  # type: ignore

from src.robeau import google_stt
from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from src.connection import socket_server
from src.core import constants as const
from src.utils import helpers

SCRIPT_NAME = helpers.construct_script_name(__file__)
HOST = "localhost"
PORT = const.SUBPROCESSES_PORTS[SCRIPT_NAME]
logger = helpers.setup_logger(SCRIPT_NAME)


class RobeauHandler(socket_server.BaseHandler):
    def __init__(self, port, script_logger):
        super().__init__(port, script_logger)
        self.stop_event = asyncio.Event()
        self.test_event = asyncio.Event()

    async def handle_message(self, message: str):
        if message == const.STOP_SUBPROCESS_MESSAGE:
            self.stop_event.set()
            self.logger.info("Received stop message")
        elif message == "test":
            self.test_event.set()
            self.logger.info("Received test message")
        else:
            await self.send_ack()


def launch_stt(interim: bool = False):
    command = (
        f'start cmd /c "cd /d {const.PROJECT_DIR_PATH} '
        f"&& set PYTHONPATH={const.PYTHONPATH} "
        f"&& .\\venv\\Scripts\\activate "
        f"&& cd {const.ROBEAU_DIR_PATH} "
        f'&& py {google_stt.SCRIPT_NAME}.py {interim}"'
    )

    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return process


async def main():
    socket_server_task = None
    try:
        handler = RobeauHandler(PORT, logger)
        launch_stt(interim=False)  # Set interim as needed
        socket_server_task = asyncio.create_task(handler.run_socket_server())
        await socket_server_task
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        raise
    finally:
        if socket_server_task:
            socket_server_task.cancel()
            await socket_server_task


if __name__ == "__main__":
    asyncio.run(main())

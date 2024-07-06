import asyncio
import logging
import subprocess

from src.conn import socks
from src.core import constants as const
from src.core import utils
from ai import google_stt

SCRIPT_NAME = utils.construct_script_name(__file__)
HOST = 'localhost'
PORT = const.SUBPROCESSES_PORTS[SCRIPT_NAME]
logger = utils.setup_logger(SCRIPT_NAME)


class RobeauHandler(socks.BaseHandler):
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
            print(message)
        await self.send_ack()


def launch_stt(interim: bool = True):
    command = (f'start cmd /c "cd /d {const.PROJECT_DIR_PATH} '
               f'&& set PYTHONPATH={const.PYTHONPATH} '
               f'&& .\\venv\\Scripts\\activate '
               f'&& cd {const.AI_DIR_PATH} '
               f'&& py {google_stt.SCRIPT_NAME}.py {interim}"')

    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    return process


async def main():
    socket_server_task = None
    stt_process = None
    try:
        handler = RobeauHandler(PORT, logger)
        stt_process = launch_stt(interim=False)
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
        if stt_process:
            stt_process.terminate()


if __name__ == "__main__":
    asyncio.run(main())

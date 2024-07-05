import asyncio
import subprocess

from src.conn import socks
from src.core import constants as const
from src.core import utils
from src.scripts import google_stt

SCRIPT_NAME = utils.construct_script_name(__file__)
HOST = 'localhost'
PORT = const.SUBPROCESSES_PORTS[SCRIPT_NAME]
logger = utils.setup_logger(SCRIPT_NAME)


class RobeauHandler(socks.BaseHandler):
    def __init__(self, port, logger_instance):
        super().__init__(port, logger_instance)
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
            self.logger.info(f"Received: {message}")
            print(message)
        await self.send_ack()


def launch_stt():
    command = (f'start cmd /k "cd /d {const.PROJECT_DIR_PATH} '
               f'&& set PYTHONPATH={const.PYTHONPATH} '
               f'&& .\\venv\\Scripts\\activate '
               f'&& cd {const.SCRIPTS_DIR_PATH} '
               f'&& py {google_stt.SCRIPT_NAME}.py"')

    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    return process


async def main():
    handler = RobeauHandler(PORT, logger)
    launch_stt()
    server_task = await asyncio.create_task(socks.run_socket_server(handler))
    await server_task


if __name__ == "__main__":
    asyncio.run(main())

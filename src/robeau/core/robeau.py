import asyncio
import logging
import subprocess
from src.core.constants import STRING_WITH_SYNS_FILE_PATH

from neo4j import Session
from sbert_matcher import SBERTMatcher  # type: ignore

from src.connection import socket_server
from src.core import constants as const
from src.robeau.core import google_stt
from src.robeau.core.graph_logic_network import (
    USER,
    ConversationState,
    cleanup,
    initialize,
    process_node,
)
from src.utils import helpers

SCRIPT_NAME = helpers.construct_script_name(__file__)
HOST = "localhost"
PORT = const.SUBPROCESSES_PORTS[SCRIPT_NAME]
STRING_WITH_SYNS = STRING_WITH_SYNS_FILE_PATH
logger = helpers.setup_logger(SCRIPT_NAME)

# Initialize SBERT matcher
sbert_matcher = SBERTMatcher(file_path=STRING_WITH_SYNS, similarity_threshold=0.65)


class RobeauHandler(socket_server.BaseHandler):
    def __init__(
        self,
        port,
        logger,
        session: Session,
        conversation_state: ConversationState,
        show_details=False,
    ):
        super().__init__(port, logger)
        self.stop_event = asyncio.Event()
        self.session = session
        self.conversation_state = conversation_state
        self.show_details = show_details

    async def handle_message(self, message: str):
        if message == const.STOP_SUBPROCESS_MESSAGE:
            self.stop_event.set()
            self.logger.info("Received stop message")
            return

        message = sbert_matcher.check_for_best_matching_synonym(
            message, self.show_details
        )

        process_node(
            session=self.session,
            node=message,
            conversation_state=self.conversation_state,
            source=USER,
        )


def launch_google_stt(interim: bool = False, socket: str = "robeau"):
    command = (
        f'start cmd /c "cd /d {const.PROJECT_DIR_PATH} '
        f"&& set PYTHONPATH={const.PYTHONPATH} "
        f"&& .\\venv\\Scripts\\activate "
        f"&& cd {const.ROBEAU_DIR_PATH}\\core "
        f'&& py {google_stt.SCRIPT_NAME}.py --interim {interim} --socket {socket}"'
    )

    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return process


async def main(show_details=False):
    socket_server_task = None
    try:
        driver, session, conversation_state, stop_event, update_thread = initialize()
        handler = RobeauHandler(PORT, logger, session, conversation_state, show_details)
        launch_google_stt(interim=False, socket="robeau")  # Set interim as needed
        socket_server_task = asyncio.create_task(handler.run_socket_server())
        await socket_server_task
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        raise
    finally:
        cleanup(driver, session, stop_event, update_thread)
        if socket_server_task:
            socket_server_task.cancel()
            await socket_server_task


if __name__ == "__main__":
    asyncio.run(main(show_details=True))

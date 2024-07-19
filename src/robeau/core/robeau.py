import asyncio
import logging
import re
import subprocess

from neo4j import Session

from src.connection.socket_server import BaseHandler
from src.core.constants import (
    PROJECT_DIR_PATH,
    PYTHONPATH,
    ROBEAU_DIR_PATH,
    STOP_SUBPROCESS_MESSAGE,
    SUBPROCESSES_PORTS,
)
from src.robeau.classes.sbert_matcher import SBERTMatcher  # type: ignore
from src.robeau.core import google_stt
from src.robeau.core.constants import STRING_WITH_SYNS_FILE_PATH
from src.robeau.core.graph_logic_network import (
    GREETING,
    USER,
    ConversationState,
    cleanup,
    initialize,
    process_node,
)
from src.utils import helpers

SCRIPT_NAME = helpers.construct_script_name(__file__)
HOST = "localhost"
PORT = SUBPROCESSES_PORTS["robeau"]
STRING_WITH_SYNS = STRING_WITH_SYNS_FILE_PATH
logger = helpers.setup_logger(SCRIPT_NAME)

# Initialize SBERT matcher
sbert_matcher = SBERTMatcher(file_path=STRING_WITH_SYNS, similarity_threshold=0.65)


class RobeauHandler(BaseHandler):
    def __init__(
        self,
        port,
        logger,
        session: Session,
        conversation_state: ConversationState,
        show_details=False,
        check_interval=0.1,  # interval in seconds to check greeted state
    ):
        super().__init__(port, logger)
        self.stop_event = asyncio.Event()
        self.session = session
        self.conversation_state = conversation_state
        self.show_details = show_details

    async def handle_message(self, message: str):
        if message == STOP_SUBPROCESS_MESSAGE:
            await self.stop_subprocess()
            return

        if (
            not self.conversation_state.greeted
            and not self.conversation_state.expectations
            and not self.conversation_state.listens
        ):
            self.process_initial_greeting(message)
        else:
            self.process_message(message)

    async def stop_subprocess(self):
        self.stop_event.set()
        self.logger.info("Received stop message")

    def check_greeting_in_message(self, msg: str):
        words = msg.split()
        segments = [
            " ".join(words[:i]) for i in range(2, 5)
        ]  # first 2, 3, and 4 words segments
        for segment in segments:
            greeting = sbert_matcher.check_for_best_matching_synonym(
                segment, self.show_details, labels=["Greeting"]
            )
            if greeting and "hey robeau" in greeting.lower():
                return segment
        return None

    def process_initial_greeting(self, message: str):
        greeting_segment = self.check_greeting_in_message(message)
        if greeting_segment:
            remaining_message = self.extract_remaining_message(
                message, greeting_segment
            )
            if remaining_message:
                self.handle_greeting_with_message(greeting_segment, remaining_message)
            else:
                self.conversation_state.greeted = True
                self.logger.info(
                    f'Greeting "{greeting_segment}" received, ready to process messages.'
                )
                process_node(
                    session=self.session,
                    node="hey robeau",
                    conversation_state=self.conversation_state,
                    source=GREETING,
                )
        else:
            print("Waiting for greeting...")

    def extract_remaining_message(self, message: str, greeting_segment: str):
        return re.sub(re.escape(greeting_segment), "", message, count=1).strip()

    def handle_greeting_with_message(
        self, greeting_segment: str, remaining_message: str
    ):
        self.logger.info(
            f'Greeting "{greeting_segment}" and prompt "{remaining_message}" received in one message.'
        )
        matched_message = sbert_matcher.check_for_best_matching_synonym(
            remaining_message, self.show_details, labels=["Prompt"]
        )
        self.logger.info(
            f'Matched prompt "{remaining_message}" with node text: "{matched_message}"'
        )
        self.process_node_with_message(matched_message)

    def process_message(self, message: str):
        labels = self.determine_labels()
        matched_message = sbert_matcher.check_for_best_matching_synonym(
            message, self.show_details, labels=labels
        )
        self.logger.info(
            f"Matched prompt '{message}' with node text: '{matched_message if matched_message != message else None}'"  # reason for != message check is because sbert will return the same message if no sufficient match is found
        )
        self.process_node_with_message(matched_message)
        self.conversation_state.greeted = False

    def determine_labels(self):
        if self.conversation_state.listens:
            return ["Prompt", "Whisper"]
        elif self.conversation_state.expectations:
            return ["Answer"]
        else:
            return ["Prompt"]

    def process_node_with_message(self, matched_message: str):
        process_node(
            session=self.session,
            node=matched_message,
            conversation_state=self.conversation_state,
            source=USER,
        )


def launch_google_stt(interim: bool = False, socket: str = "robeau"):
    command = (
        f'start cmd /c "cd /d {PROJECT_DIR_PATH} '
        f"&& set PYTHONPATH={PYTHONPATH} "
        f"&& .\\venv\\Scripts\\activate "
        f"&& cd {ROBEAU_DIR_PATH}\\core "
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

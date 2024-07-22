import asyncio
import logging
import re
from typing import Optional

from neo4j import Session

from src.config.initialize import setup_script
from src.core.constants import SLOTS_DB_FILE_PATH
from src.robeau.classes.sbert_matcher import SBERTMatcher  # type: ignore
from src.robeau.core.constants import STRING_WITH_SYNS_FILE_PATH
from src.robeau.core.graph_logic_network import (
    GREETING,
    USER,
    ConversationState,
    cleanup,
    initialize,
    process_node,
)
from src.robeau.core.speech_recognition import recognize_speech
from src.utils.helpers import construct_script_name, setup_logger

SCRIPT_NAME = construct_script_name(__file__)


logger = setup_logger(SCRIPT_NAME)

STRING_WITH_SYNS = STRING_WITH_SYNS_FILE_PATH


# Initialize SBERT matcher
sbert_matcher = SBERTMatcher(file_path=STRING_WITH_SYNS, similarity_threshold=0.65)


class RobeauHandler:
    def __init__(
        self,
        session: Session,
        conversation_state: ConversationState,
        show_details=False,
    ):
        self.stop_event = asyncio.Event()
        self.session = session
        self.conversation_state = conversation_state
        self.show_details = show_details
        print("Waiting for greeting...")

    async def handle_message(self, message: str):
        if (
            not self.conversation_state.allows
            and not self.conversation_state.expects
            and not self.conversation_state.listens
        ):
            self.process_initial_greeting(message)
        else:
            self.process_message(message)

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
        if not greeting_segment:
            print("Waiting for greeting...")
            return

        remaining_message = self.extract_remaining_message(message, greeting_segment)
        if remaining_message:
            logger.info(
                f'Greeting "{greeting_segment}" and prompt "{remaining_message}" received in one message.'
            )
            self.greet(silent=True)
            self.handle_remaining_message(remaining_message)
        else:
            logger.info(
                f'Greeting "{greeting_segment}" received, ready to process messages.'
            )
            self.greet(silent=False)

    def extract_remaining_message(self, message: str, greeting_segment: str):
        return re.sub(re.escape(greeting_segment), "", message, count=1).strip()

    def handle_remaining_message(self, remaining_message: str):
        matched_message = sbert_matcher.check_for_best_matching_synonym(
            remaining_message, self.show_details, labels=["Prompt"]
        )
        logger.info(
            f'Matched prompt "{remaining_message}" with node text: "{matched_message}"'
        )
        self.process_node_with_message(matched_message)

    def process_message(self, message: str):
        labels = self.determine_labels()
        matched_message = sbert_matcher.check_for_best_matching_synonym(
            message, self.show_details, labels=labels
        )
        logger.info(
            f"Matched prompt '{message}' with node text: '{matched_message if matched_message != message else None}'"  # reason for != message check is because sbert will return the same message if no sufficient match is found
        )
        self.process_node_with_message(matched_message)

    def determine_labels(self):
        if self.conversation_state.listens:
            return ["Prompt", "Whisper"]
        elif self.conversation_state.expects:
            return ["Answer"]
        else:
            return ["Prompt"]

    def greet(self, silent=False):
        process_node(
            session=self.session,
            node="hey robeau",
            conversation_state=self.conversation_state,
            source=GREETING,
            silent=silent,
        )

    def process_node_with_message(self, matched_message: str):
        process_node(
            session=self.session,
            node=matched_message,
            conversation_state=self.conversation_state,
            source=USER,
            silent=False,
        )


async def main(show_details=False):
    try:
        db_conn, slot = await setup_script(SCRIPT_NAME, SLOTS_DB_FILE_PATH)
        driver, session, conversation_state, stop_event, update_thread, pause_event = (
            initialize()
        )
        handler = RobeauHandler(session, conversation_state, show_details)
        asyncio.create_task(recognize_speech(handler, pause_event))
        await handler.stop_event.wait()
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        raise
    finally:
        if db_conn:
            await db_conn.close()
        cleanup(driver, session, stop_event, update_thread)


if __name__ == "__main__":
    asyncio.run(main(show_details=True))

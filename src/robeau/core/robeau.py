import asyncio
import logging
import re

from neo4j import Session

from src.core.constants import TERMINAL_WINDOW_SLOTS_DB_FILE_PATH
from src.robeau.classes.sbert_matcher import SBERTMatcher  # type: ignore
from src.robeau.core.constants import ROBEAU_PROMPTS_JSON_FILE_PATH as ROBEAU_PROMPTS
from src.robeau.core.graph_logic_network import (
    ConversationState,
    cleanup,
    initialize,
    interrupt_robeau,
    launch_specified_query,
    robeau_is_listening,
    robeau_is_talking,
)
from src.robeau.core.speech_recognition import recognize_speech
from src.utils.initialize import setup_script
from src.utils.logging_utils import construct_script_name, setup_logger

SCRIPT_NAME = construct_script_name(__file__)


logger = setup_logger(SCRIPT_NAME)


sbert_matcher = SBERTMatcher(file_path=ROBEAU_PROMPTS, similarity_threshold=0.65)


def check_greeting_in_message(msg: str):
    """Check if first 2, 3, and 4 words segments are a greeting"""
    words = msg.split()
    segments = [" ".join(words[:i]) for i in range(2, 5)]
    for segment in segments:
        greeting, _ = sbert_matcher.check_for_best_matching_synonym(
            segment, show_details=True, labels=["Greeting"]
        )
        if greeting and "hey robeau" in greeting.lower():
            return segment
    return None


def check_for_stop_command(message: str):
    stop_command, data = sbert_matcher.check_for_best_matching_synonym(
        message,
        show_details=True,
        labels=["StopCommand", "StopCommandRude", "StopCommandPolite"],
    )
    rudeness_points = data.get("rudeness_points", None)
    return stop_command, rudeness_points


def extract_remaining_message(message: str, greeting_segment: str):
    remaining_message = re.sub(
        re.escape(greeting_segment), "", message, count=1
    ).strip()

    if remaining_message:
        logger.info(
            f'Greeting "{greeting_segment}" and prompt "{remaining_message}" received in one message.'
        )
    else:
        logger.info(
            f'Greeting "{greeting_segment}" received, ready to process messages.'
        )
    return remaining_message


def log_matching_synonym(matched_message: str | None, message: str):
    if matched_message:
        logger.info(f"Matched prompt '{message}' with node text: '{matched_message}")
    else:
        logger.info(f"Could not match prompt '{message}' with any node text.")


class RobeauHandler:
    def __init__(
        self,
        session: Session,
        conversation_state: ConversationState,
    ):
        self.stop_event = asyncio.Event()
        self.session = session
        self.conversation_state = conversation_state
        print("Waiting for greeting...")

    async def handle_message(self, message: str):

        if robeau_is_talking.is_set():
            print("Robeau is talking.")
            stop_command, rudeness_points = check_for_stop_command(message)
            if stop_command:
                interrupt_robeau()
                print(f"interrupted robeau with {rudeness_points} rudeness points")
            else:
                print("No stop command detected over robeau's speech")

        elif not robeau_is_listening(self.conversation_state):
            self.process_initial_greeting(message)

        else:
            self.process_message(message)

    def process_initial_greeting(self, message: str):
        greeting_segment = check_greeting_in_message(message)
        if not greeting_segment:
            print("Waiting for greeting...")
            return

        remaining_message = extract_remaining_message(message, greeting_segment)

        if remaining_message:
            self.greet(silent=True)
            self.handle_remaining_message(remaining_message)
        else:
            self.greet(silent=False)

    def handle_remaining_message(self, remaining_message: str):
        matched_message, _ = sbert_matcher.check_for_best_matching_synonym(
            remaining_message, show_details=True, labels=["Prompt"]
        )
        log_matching_synonym(matched_message, remaining_message)
        if matched_message:
            self.process_node_with_message(matched_message)

    def process_message(self, message: str):
        labels = self.determine_labels()
        matched_message, _ = sbert_matcher.check_for_best_matching_synonym(
            message, show_details=True, labels=labels
        )
        log_matching_synonym(matched_message, message)
        if matched_message:
            self.process_node_with_message(matched_message)

    def determine_labels(self):
        labels = []
        if self.conversation_state.context["listens"]:
            labels.append("Whisper")

        if self.conversation_state.context["expects"]:
            labels.append("Answer")

        if self.conversation_state.context["allows"]:
            labels.append("Prompt")

        if self.conversation_state.context["permits"]:
            labels.append("Plea")

        return labels

    def greet(self, silent=False):
        launch_specified_query(
            user_query="hey robeau",
            query_type="greeting",
            session=self.session,
            conversation_state=self.conversation_state,
            silent=silent,
        )

    def process_node_with_message(self, matched_message: str):
        launch_specified_query(
            user_query=matched_message,
            query_type="regular",
            session=self.session,
            conversation_state=self.conversation_state,
            silent=False,
        )


async def main():
    try:
        db_conn, _ = await setup_script(SCRIPT_NAME, TERMINAL_WINDOW_SLOTS_DB_FILE_PATH)
        driver, session, conversation_state, stop_event, update_thread, pause_event = (
            initialize()
        )
        handler = RobeauHandler(session, conversation_state)
        recognize_task = asyncio.create_task(recognize_speech(handler, pause_event))
        await handler.stop_event.wait()
        await recognize_task

    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        raise
    finally:
        if db_conn:
            await db_conn.close()
        cleanup(driver, session, stop_event, update_thread)


if __name__ == "__main__":
    asyncio.run(main())

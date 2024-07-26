import random
import threading
import time
from collections import defaultdict
from logging import DEBUG, INFO, Logger
from threading import Thread
from typing import Optional
from typing import Literal

from neo4j import GraphDatabase, Result, Session
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from src.robeau.classes.audio_player import AudioPlayer
from src.robeau.classes.graph_logic_constants import (
    ANY_MATCHING_PROMPT,
    EXPECTATIONS_FAILURE,
    EXPECTATIONS_SET,
    EXPECTATIONS_SUCCESS,
    GREETING,
    MODIFIER,
    NO_MATCHING_PROMPT_OR_WHISPER,
    RESET_EXPECTATIONS,
    ROBEAU,
    SET_ROBEAU_UNRESPONSIVE,
    SET_ROBEAU_STUBBORN,
    SYSTEM,
    USER,
    PROLONG_STUBBORN,
    ANY_RELEVANT_USER_INPUT,
    ANY_MATCHING_PLEA,
    ROBEAU_NO_MORE_STUBBORN,
    ANY_MATCHING_WHISPER,
    QuerySource,
    transmission_output_nodes,
)
from src.robeau.core.constants import AUDIO_MAPPINGS_FILE_PATH
from src.utils.helpers import construct_script_name, setup_logger

SCRIPT_NAME = construct_script_name(__file__)
logger = setup_logger(SCRIPT_NAME, level=DEBUG)


class ConversationState:
    def __init__(self, logger: Logger):
        self.test_value = False
        self.logger = logger
        self.lock = threading.Lock()
        # states
        self.cutoff = False
        # time-bound states
        self.stubborn = {
            "state": False,
            "duration": 0.0,
            "time_left": None,
            "start_time": 0.0,
        }
        self.unresponsive = {
            "state": False,
            "duration": 0.0,
            "time_left": None,
            "start_time": 0.0,
        }

        self.context: dict[str, list[dict]] = {
            "allows": [],
            "permits": [],
            "locks": [],
            "unlocks": [],
            "expects": [],
            "primes": [],
            "unprimes": [],
            "listens": [],
            "initiates": [],
        }

    def _add_item(
        self, node: str, labels: list[str], duration: float | None, item_type: str
    ):
        start_time = time.time()
        item_list = self.context[item_type]

        for existing_item in item_list:
            if existing_item["node"] == node:
                if duration is None:  # None means infinite duration here
                    return

                # Reset duration if the item already exists
                existing_item["duration"] = duration
                existing_item["time_left"] = duration
                existing_item["start_time"] = start_time
                self.logger.info(f"Reset the time duration of {existing_item}")
                return

        item = {
            "type": item_type,
            "node": node,
            "labels": labels,
            "time_left": duration,
            "duration": duration,
            "start_time": start_time,
        }

        item_list.append(item)
        self.logger.info(f"Added {item_type} << {node} >> {labels}: {item}")

    def add_item(
        self, node: str, labels: list[str], duration: float | None, item_type: str
    ):
        if item_type in self.context.keys():
            self._add_item(node, labels, duration, item_type)
        else:
            raise ValueError(
                f"Key from {node} = {item_type} does not match context keys: {self.context.keys()} "
            )

    def delay_item(self, node: str, labels: list[str], duration: float | None):
        """Unused right now but may be used in the future, Logic wise just know that the difference between this and add_initiation is that this is for items that are already in the conversation state, which means a previously processed node wont be processed again if they are pointed to with a DELAY relationship"""
        for item_type, node_list in self.context.items():
            for item in node_list:
                if item["node"] == node:
                    self._add_item(node, labels, duration, item_type)

    def disable_item(self, node: str):
        for node_list in self.context.values():
            for item in node_list:
                if item["node"] == node:
                    node_list.remove(item)
                    self.logger.info(f"Item disabled: {item}")
                    return

    def set_state(
        self, state_name: Literal["stubborn", "unresponsive"], duration: float
    ):
        state_obj = getattr(self, state_name, None)
        if state_obj:
            state_obj["state"] = True
            state_obj["duration"] = duration
            state_obj["start_time"] = time.time()
            state_obj["time_left"] = duration
            self.logger.info(f"Set state {state_name} for {duration} seconds")
        else:
            logger.error(f"Invalid state name {state_name}")

    def _update_time_left(self, item: dict):
        current_time = time.time()
        start_time = item["start_time"]
        duration = item["duration"]
        time_left = item["time_left"]

        if time_left is not None:
            elapsed_time = current_time - start_time
            remaining_time = max(0, duration - elapsed_time)
            item["time_left"] = remaining_time

    def _remove_expired(
        self,
        items: list[dict],
        log_messages: list[str],
        session: Session,
        key: str,
    ) -> list[dict]:
        valid_items = []
        expired_items = []
        complete_initiations = []

        for item in items:
            self._update_time_left(item)
            time_left = item.get("time_left")
            item_type = item.get("type")
            node = item.get("node")
            labels = item.get("labels", [])

            if time_left is None or time_left > 0:
                valid_items.append(item)
                if time_left is not None:
                    log_messages.append(
                        f"{item_type}: {labels}: << {node} >> ({time_left:.2f}): {item}"
                    )
            else:
                expired_items.append(item)
                if item_type == "initiates":
                    complete_initiations.append(item)
                    self.logger.info(f"Initiation complete: {item}")
                else:
                    self.logger.info(f"Item {item_type} has expired: {item}")

        if complete_initiations:
            for initiation in complete_initiations:
                activate_connection_or_item(initiation, self, "item")
                process_node(
                    session, initiation["node"], self, source=ROBEAU, main_call=True
                )

        items_after_inits = self.context[key]
        valid_items = [item for item in items_after_inits if item not in expired_items]

        return valid_items

    def _update_timed_items(
        self,
        session: Session,
        log_messages: list[str],
    ):
        for key in self.context:
            updated_items = self._remove_expired(
                self.context[key], log_messages, session, key
            )
            self.context[key] = updated_items

    def _update_timed_states(self, session: Session, log_messages: list[str]):
        states_to_update = ["stubborn", "unresponsive"]

        for state in states_to_update:
            state_obj = getattr(self, state)
            self._update_time_left(state_obj)
            time_left = state_obj.get("time_left")
            enabled_state = state_obj["state"]

            if not enabled_state:
                continue

            if time_left > 0:
                log_messages.append(f"State {state}: ({time_left:.2f}): {state_obj}")
            else:
                state_obj["state"] = False
                logger.info(f"Robeau is no longer in state {state} ")
                if state == "stubborn":
                    process_node(
                        session=session,
                        node=ROBEAU_NO_MORE_STUBBORN,
                        conversation_state=self,
                        source=SYSTEM,
                    )

            setattr(self, state, state_obj)

    def update_conversation_state(self, session: Session):
        log_messages: list[str] = []

        self._update_timed_items(session, log_messages)
        self._update_timed_states(session, log_messages)

        if log_messages:
            self.logger.info("Time-bound updates:\n" + "\n".join(log_messages) + "\n")
        else:
            self.logger.info("No time-bound items or states to update")

    def reset_attribute(self, *attributes: str):
        reset_attributes = []

        for attribute in attributes:
            if attribute in self.context:
                self.context[attribute] = []
                reset_attributes.append(attribute)
            else:
                self.logger.error(f"Invalid attribute: {attribute}")

        if reset_attributes:
            self.logger.info(f"Reset attributes: {', '.join(reset_attributes)}")

    def apply_definitions(self, session: Session, node: str):
        process_node(
            session=session,
            node=node,
            source=MODIFIER,
            conversation_state=self,
            silent=True,
        )

    def revert_definitions(self, session: Session, node: str):
        definitions_to_revert = (
            get_node_connections(
                session, text=node, source=MODIFIER, conversation_state=self
            )
            or []
        )
        formatted_definitions = [
            (i["start_node"], i["relationship"], i["end_node"])
            for i in definitions_to_revert
        ]
        self.logger.info(f"Obtained definitions to revert: {formatted_definitions}")

        for connection in definitions_to_revert:
            end_node = connection.get("end_node", "")
            self._revert_individual_definition(end_node)

    def _revert_individual_definition(self, node: str):
        for definition_type, definitions in self.context.items():
            initial_count = len(definitions)
            definitions[:] = [
                definition for definition in definitions if definition["node"] != node
            ]
            if len(definitions) < initial_count:
                self.logger.info(f"Removed {definition_type}: << {node} >>")

    def log_conversation_state(self):
        log_message = []

        states = {"stubborn": self.stubborn, "unresponsive": self.unresponsive}

        if not any(self.context.values()) and not (
            any([state["state"] for state in states.values()])
        ):
            log_message.append("No items in conversation state")

        log_message.append("Conversation state:")
        for item_type, items in self.context.items():
            for item in items:
                node = item["node"]
                time_left = item.get("time_left")
                labels = item.get("labels", [])
                time_left_str = (
                    f"{time_left:.2f}" if time_left is not None else "Infinite"
                )
                log_message.append(
                    f"{item_type}: {labels}: << {node} >> ({time_left_str}): {item}"
                )

        for state_name, state in states.items():
            time_left = state.get("time_left")
            time_left_str = f"{time_left:.2f}" if time_left is not None else "Infinite"
            state_str = f"State {state_name} ({time_left_str}) : {state} "
            if state["state"]:
                log_message.append(state_str)

        log_message[1:] = sorted(log_message[1:])

        self.logger.info("\n".join(log_message) + "\n")


audio_player = AudioPlayer(AUDIO_MAPPINGS_FILE_PATH, logger=logger)
audio_finished_event = threading.Event()
audio_started_event = threading.Event()
first_callback_made = threading.Event()

node_thread: Thread | None = None


def get_node_data(
    session: Session,
    text: str,
    labels: list[str],
    conversation_state: ConversationState,
    source: QuerySource,
) -> Result | None:

    def process_no_matching_prompt_or_whisper():
        process_node(
            session, NO_MATCHING_PROMPT_OR_WHISPER, conversation_state, source=SYSTEM
        )

    labels_query = "|".join(labels)
    query = f"""
    MATCH (x:{labels_query})-[r]->(y)
    WHERE toLower(x.text) = toLower($text)
    RETURN x, r, y
    """
    result = session.run(query, text=text)

    if source == USER:
        if not result.peek() and ("Prompt" in labels or "Whisper" in labels):
            process_no_matching_prompt_or_whisper()

    return result if result.peek() else None


def define_labels_and_text(
    session: Session,
    text: str,
    conversation_state: ConversationState,
    source: QuerySource,
) -> tuple[list[str], str]:

    context_specifications = ["[stub]", "[example]"]

    def check_for_any_relevant_user_input():
        def text_in_conversation_context() -> bool:
            lower_text = text.lower()
            first_check = any(
                lower_text == dictionary["node"].lower()
                for list_of_dicts in conversation_state.context.values()
                for dictionary in list_of_dicts
            )
            if first_check:
                return True

            for spec in context_specifications:
                combined_text = lower_text + " " + spec
                second_check = any(
                    combined_text == dictionary["node"].lower()
                    for dictionary in conversation_state.context.get("listens", [])
                )
                if second_check:
                    return True

            return False

        if text_in_conversation_context():
            process_node(
                session, ANY_RELEVANT_USER_INPUT, conversation_state, source=SYSTEM
            )

    def prompt_meets_expectations():
        if any(
            text.lower() == item["node"].lower()
            for item in conversation_state.context["expects"]
        ):
            logger.info(f" << {text} >> meets conversation expectations")
            process_node(
                session, EXPECTATIONS_SUCCESS, conversation_state, source=SYSTEM
            )
            return True
        else:
            logger.info(f" << {text} >> does not meet conversation expectations")
            process_node(
                session, EXPECTATIONS_FAILURE, conversation_state, source=SYSTEM
            )
            return False

    def prompt_matches_allows():
        if any(
            text.lower() == item["node"].lower()
            for item in conversation_state.context["allows"]
        ):
            process_node(
                session, ANY_MATCHING_PROMPT, conversation_state, source=SYSTEM
            )
            return True

    def prompt_matches_whispers(context: Optional[str] = None):
        if any(
            text.lower() + (" " + context) if context else "" == item["node"].lower()
            for item in conversation_state.context["listens"]
        ):
            process_node(
                session, ANY_MATCHING_WHISPER, conversation_state, source=SYSTEM
            )
            return True

    def prompt_matches_pleas():
        if any(
            text.lower() == item["node"].lower()
            for item in conversation_state.context["permits"]
        ):
            process_node(session, ANY_MATCHING_PLEA, conversation_state, source=SYSTEM)
            return True

    labels = []
    modified_text = ""
    if source == USER:

        check_for_any_relevant_user_input()

        # When answering a question, only check for expects
        if conversation_state.context["expects"] and prompt_meets_expectations():
            labels.append("Answer")
            return labels, modified_text

        # When in a stubborn context:
        if conversation_state.stubborn["state"]:
            # Check for pleas before allows (it's required for a few connections proper priority)
            if prompt_matches_pleas():
                labels.append("Plea")
                return labels, modified_text

            # Check for attempt to prompt without pleading
            if prompt_matches_allows() and not prompt_matches_pleas():
                # TODO, in the future. Implement a way to still accept some prompts when stubborn, but reluctantly
                return labels, modified_text

            # Check for whispers and modify the text to match the DB value in the stubborn context
            if prompt_matches_whispers(context="[stub]"):
                labels.append("Whisper")
                modified_text = text + " " + "[stub]"

            return labels, modified_text

        # If in no particular context, match for regular prompts and whispers.
        if prompt_matches_allows():
            labels.append("Prompt")

        if prompt_matches_whispers():
            labels.append("Whisper")

    elif source == GREETING:
        labels.append("Greeting")

    elif source == ROBEAU:
        labels.extend(
            ["Response", "Question", "LogicGate", "Greeting", "Output", "TrafficGate"]
        )

    elif source == SYSTEM:
        labels.append("Input")

    elif source == MODIFIER:
        labels.extend(
            [
                "Prompt",
                "Whisper",
                "Answer",
                "Greeting",
                "Response",
                "Question",
                "LogicGate",
                "Input",
                "Output",
                "TrafficGate",
                "Plea",
            ]
        )

    return labels, modified_text


def get_node_connections(
    session: Session,
    text: str,
    conversation_state: ConversationState,
    source: QuerySource,
) -> list[dict] | None:

    labels, modified_text = define_labels_and_text(
        session, text, conversation_state, source
    )

    if not labels:
        labels = [
            "None"
        ]  # This will return no results from the database, but it will also not throw an error. We still want to call get_node_data (instead of making an early return) in order to call relevant nested functions inside.

    if modified_text:  # Used only for [context] tags in case of duplicate nodes
        text = modified_text

    logger.info(f"Labels for fetching {text} connection are {labels}")

    result = get_node_data(session, text, labels, conversation_state, source)

    if not result:
        return None

    result_data = [
        {
            "id": index,
            "start_node": dict(record["x"])["text"],
            "relationship": record["r"].type,
            "end_node": dict(record["y"])["text"],
            "params": dict(record["r"]),
            "labels": {
                "start": list(record["x"].labels),
                "end": list(record["y"].labels),
            },
        }
        for index, record in enumerate(result)
    ]

    return result_data


def wait_for_audio_to_play(response_nodes_reached: list[str]):
    logger.info(
        f"Stopping to wait for audio to play for nodes: {response_nodes_reached} "
    )
    audio_finished_event.wait()
    audio_player.join_threads()
    audio_started_event.clear()
    logger.info(
        f"Finished waiting for audio to play for nodes: {response_nodes_reached} "
    )


def play_audio(node: str, conversation_state: ConversationState):

    def on_start():
        audio_started_event.set()
        first_callback_made.set()
        conversation_state.cutoff = False

    def on_stop():
        audio_finished_event.set()
        first_callback_made.set()
        conversation_state.cutoff = True

    def on_end():
        audio_finished_event.set()
        first_callback_made.set()

    def on_error():
        first_callback_made.set()
        conversation_state.cutoff = False

    audio_player.set_callbacks(
        on_start=on_start,
        on_stop=on_stop,
        on_end=on_end,
        on_error=on_error,
    )
    audio_player.play_audio(node)
    logger.info(f"Waiting for first callback")
    first_callback_made.wait()
    logger.info(f"First callback received, let's go")
    first_callback_made.clear()


def activate_connection_or_item(
    node_dict: dict,
    conversation_state: ConversationState,
    dict_type: Literal["connection", "item"],
):
    """Works for both activation connections (end_node) and dictionaries from the conversation state(node)."""
    node = node_dict.get("end_node", "") or node_dict.get("node", "")
    print(node if node else "ERROR: No node found in connection or item")

    node_labels = (
        node_dict.get("labels", {}).get("end", "")
        if dict_type == "connection"
        else node_dict.get("labels", "")
    )
    vocal_labels = ["Response", "Question", "Test"]

    if any(label in vocal_labels for label in node_labels):
        play_audio(node, conversation_state)
    else:
        logger.info(
            f" << {node} >> with labels {node_labels} is not considered an audio output"
        )

    return node_dict


def process_logic_activations(
    session: Session,
    connections: list[dict],
    logic_gate: str,
    conversation_state: ConversationState,
):
    if not connections:
        logger.error(f'No "THEN" connection found for LogicGate: << {logic_gate} >>')
        return

    for connection in connections:
        activate_connection_or_item(connection, conversation_state, "item")
        process_node(session, connection["end_node"], conversation_state, ROBEAU)


def process_and_logic_checks(connections: list[dict], attribute: list[dict]):
    return all(
        any(connection["end_node"] == item["node"] for item in attribute)
        for connection in connections
    )


def process_initial_logic_check(connection: dict, attribute: list[dict]):
    return any(connection["end_node"] == item["node"] for item in attribute)


def filter_logic_connections(connections: list[dict], logic_gate: str):
    attribute_map = {
        "IS_ALLOWED": "allows",
        "IS_PERMITTED": "permits",
        "IS_LOCKED": "locks",
        "IS_UNLOCKED": "unlocks",
        "IS_EXPECTED": "expects",
        "IS_PRIMED": "primes",
        "IS_UNPRIMED": "unprimes",
        "IS_LISTENED": "listens",
        "IS_INITIATED": "initiates",
    }

    and_conditions_rel = {"AND_" + key for key in attribute_map.keys()}

    initial_conn = None
    and_conns = []
    then_conns = []
    other_conns = []

    for conn in connections:
        if conn["relationship"] in attribute_map:
            initial_conn = conn
        elif conn["relationship"] in and_conditions_rel:
            and_conns.append(conn)
        elif conn["relationship"] == "THEN":
            then_conns.append(conn)
        else:
            other_conns.append(conn)
            logger.warning(f"Atypical connection for logicGate {logic_gate}: {conn}")

        formatted_and_conns = "\n".join([str(and_conn) for and_conn in and_conns])
        formatted_then_conns = "\n".join([str(then_conn) for then_conn in then_conns])

    logger.info(
        f"LogicGate << {logic_gate} >> connections: \nInitial: {initial_conn} \nAnd: {formatted_and_conns} \nThen: {formatted_then_conns}"
    )
    return initial_conn, and_conns, then_conns


def determine_attribute(conversation_state: ConversationState, relationship: dict):
    attribute_map = {
        "IS_ALLOWED": "allows",
        "IS_PERMITTED": "permits",
        "IS_LOCKED": "locks",
        "IS_UNLOCKED": "unlocks",
        "IS_EXPECTED": "expects",
        "IS_PRIMED": "primes",
        "IS_UNPRIMED": "unprimes",
        "IS_LISTENED": "listens",
        "IS_INITIATED": "initiates",
    }
    for key, attribute_name in attribute_map.items():
        if key in relationship:
            return conversation_state.context.get(attribute_name)
    return None


def process_logic_connections(
    session: Session,
    connections: list[dict],
    logic_gate: str,
    conversation_state: ConversationState,
):
    initial_conn, and_conns, then_conns = filter_logic_connections(
        connections, logic_gate
    )

    if not initial_conn:
        logger.error(f"No initial connection found for LogicGate: {logic_gate}")
        return

    attribute = determine_attribute(conversation_state, initial_conn["relationship"])
    if not attribute:
        logger.error(
            f"Could not determine attribute for relationship: {initial_conn['relationship']}. (attribute was: '{attribute}')"
        )
        return

    if not process_initial_logic_check(initial_conn, attribute):
        return

    if and_conns and not process_and_logic_checks(and_conns, attribute):
        return

    process_logic_activations(session, then_conns, logic_gate, conversation_state)


def process_logic_relationships(
    session: Session, relations_map: dict, conversation_state: ConversationState
):
    if not relations_map.get("IF"):
        return

    for if_connection in relations_map["IF"]:
        logic_gate = if_connection["end_node"]
        gate_connections = get_node_connections(
            session, logic_gate, conversation_state, ROBEAU
        )

        if not gate_connections:
            logger.info(f"No connections found for LogicGate: {logic_gate}")
            continue

        process_logic_connections(
            session, gate_connections, logic_gate, conversation_state
        )


def process_modifications_connections(
    session: Session,
    connections: list[dict],
    process_method,
):
    for connection in connections:
        end_node = connection.get("end_node", "")
        labels = connection.get("labels", {}).get("end", [])
        duration = connection.get("params", {}).get("duration")
        process_method(end_node, labels, duration, session)


def process_modifications_relationships(
    session: Session,
    relationships_map: dict[str, list[dict]],
    conversation_state: ConversationState,
):
    relationship_methods = {
        "DELAYS": lambda end_node, labels, duration, session: conversation_state.delay_item(
            end_node, labels, duration
        ),  # Unused right now but may be used in the future
        "DISABLES": lambda end_node, labels, duration, session: conversation_state.disable_item(
            end_node
        ),
        "APPLIES": lambda end_node, labels, duration, session: conversation_state.apply_definitions(
            session, end_node
        ),
        "REVERTS": lambda end_node, labels, duration, session: conversation_state.revert_definitions(
            session, end_node
        ),
    }

    for relationship, process_method in relationship_methods.items():
        connections = relationships_map.get(relationship, [])
        if connections:
            process_modifications_connections(session, connections, process_method)


def process_definitions_connections(connections: list[dict], method):
    for connection in connections:
        node = connection.get("end_node", "")
        duration = connection.get("params", {}).get("duration")
        labels = connection.get("labels", {}).get("end", [])
        method(node, labels, duration)


def process_definitions_relationships(
    session: Session,
    relationships_map: dict[str, list[dict]],
    conversation_state: ConversationState,
):
    for relationship, connections in relationships_map.items():
        relationship_lower = relationship.lower()
        if relationship_lower in conversation_state.context:
            for connection in connections:
                node = connection.get("end_node")
                duration = connection.get("params", {}).get("duration")
                labels = connection.get("labels", {}).get("end", [])
                if not node:
                    logger.error(f"No end node for connection {connection}")
                    continue
                conversation_state.add_item(node, labels, duration, relationship_lower)

    if relationships_map["EXPECTS"]:
        process_node(
            session=session,
            node=EXPECTATIONS_SET,
            conversation_state=conversation_state,
            source=SYSTEM,
        )


def activate_connections(
    connections: list[dict],
    conversation_state: ConversationState,
    random_source: bool = False,
):
    conn_names = [connection["end_node"] for connection in connections]
    status = "random" if random_source else "non-random"
    if len(conn_names) > 0:
        logger.info(
            f"Activating {len(connections)} {status} connection(s): {conn_names}"
        )
    for connection in connections:
        activate_connection_or_item(connection, conversation_state, "connection")
    return connections


def select_random_connection(connections: list[dict] | dict) -> dict:
    if isinstance(connections, dict):  # only one connection passed
        logger.info(f"Only one connection passed: {connections}")
        return connections

    weights = [
        connection.get("params", {}).get("randomWeight") for connection in connections
    ]

    if None in weights:
        logger.warning(
            f"Missing weight(s) for {connections}. Selecting random connection..."
        )
        return random.choice(connections)

    total_weight = sum(weights)
    chosen_weight = random.uniform(0, total_weight)
    current_weight = 0

    for connection, weight in zip(connections, weights):
        current_weight += weight
        if current_weight >= chosen_weight:
            return connection

    logger.error(
        "Failed to select a connection, returning a random choice as fallback."
    )
    return random.choice(connections)


def select_random_connections(random_pool_groups: list[list[dict]]) -> list[dict]:
    selected_connections = []

    for pooled_group in random_pool_groups:
        connection = select_random_connection(pooled_group)
        pool_id = connection["params"].get("randomPoolId")
        end_node = connection["end_node"]
        logger.info(
            f"Selected response for random pool Id {pool_id} is: << {end_node} >>"
        )
        selected_connections.append(connection)

    return selected_connections


def define_random_pools(connections: list[dict]) -> list[list[dict]]:
    grouped_data = defaultdict(list)

    for connection in connections:
        random_pool_id = connection["params"].get("randomPoolId", 0)
        grouped_data[random_pool_id].append(connection)

    result = list(grouped_data.values())

    if result:
        formatted_pools = "\n".join(
            f"\ngroup{index}:\n" + "\n".join(map(str, group))
            for index, group in enumerate(result)
        )
        logger.info(f"Random pools defined: {formatted_pools}")

    return result


def process_random_connections(
    random_connection: list[dict], conversation_state: ConversationState
) -> list[dict]:
    random_pool_groups: list[list[dict]] = define_random_pools(random_connection)
    selected_connections: list[dict] = select_random_connections(random_pool_groups)
    activate_connections(selected_connections, conversation_state, random_source=True)
    return selected_connections


def execute_attempt(
    connection: dict,
    node: str,
    conversation_state: ConversationState,
):
    if any(
        node == item["node"] for item in conversation_state.context["unlocks"]
    ) or any(node == item["node"] for item in conversation_state.context["primes"]):
        logger.info(
            f"Successful attempt at connection: {list(connection.values())[1:4]}"
        )
        return True
    else:
        logger.info(f"Failed attempt at connection: {list(connection.values())[1:4]}")
    return False


def node_is_unaccessible(
    node: str, connection: dict, conversation_state: ConversationState
):
    conn_locked = any(
        node == item["node"] for item in conversation_state.context["locks"]
    )
    conn_unprimed = any(
        node == item["node"] for item in conversation_state.context["unprimes"]
    )

    if conn_locked:
        logger.info(f"Connection is locked: {list(connection.values())[1:4]}")
    if conn_unprimed:
        logger.info(f"Connection is unprimed: {list(connection.values())[1:4]}")

    return any([conn_locked, conn_unprimed])


def process_activation_connections(
    connections: list[dict],
    conversation_state: ConversationState,
    connection_type: str,
) -> list[dict]:
    random_connections = []
    regular_connections = []
    activated_connections = []

    for connection in connections:
        node = connection["end_node"]
        if node_is_unaccessible(node, connection, conversation_state):
            continue

        if connection_type == "ATTEMPTS" and not execute_attempt(
            connection, node, conversation_state
        ):
            continue

        if connection.get("params", {}).get("randomWeight"):
            random_connections.append(connection)
        else:
            regular_connections.append(connection)

    activated_connections.extend(
        process_random_connections(random_connections, conversation_state)
    )
    activated_connections.extend(
        activate_connections(
            regular_connections, conversation_state, random_source=False
        )
    )

    if activated_connections:
        conversation_state.reset_attribute("primes", "unprimes")

    return activated_connections


def process_activation_relationships(
    relationships_map: dict[str, list[dict]],
    conversation_state: ConversationState,
    cutoff: Optional[bool] = False,
) -> list[str]:
    priority_order = ["CHECKS", "ATTEMPTS", "TRIGGERS", "DEFAULTS"]
    end_nodes_reached = []

    if cutoff:
        priority_order = ["CUTSOFF"] + priority_order

    for key in priority_order:
        if relationships_map[key]:
            activated = process_activation_connections(
                relationships_map[key],
                conversation_state,
                connection_type=key,
            )
            if activated:
                end_nodes_reached.extend([item["end_node"] for item in activated])
                break  # Stop processing further as we've found the first activated connections

    return end_nodes_reached


def process_relationships(
    session: Session,
    connections: list[dict],
    conversation_state: ConversationState,
    node: str,
    source: QuerySource,
    silent: Optional[bool] = False,
    cutoff: Optional[bool] = False,
) -> list[str]:

    def log_formatted_connections(relationships_map: dict[str, list[dict]]):
        all_connections = []
        for connection in relationships_map.values():
            all_connections.extend(connection)

        formatted_connections = "\n".join(
            [str(connection) for connection in all_connections]
        )
        formatted_silent_connections = "\n".join(
            [
                str(connection)
                for connection in all_connections
                if connection["relationship"]
                not in ("CHECKS", "ATTEMPTS", "TRIGGERS", "DEFAULTS", "CUTSOFF")
            ]
        )
        if not silent and all_connections:
            logger.info(
                f"Processing connections for node << {node} >> from source {source.name}:\n{formatted_connections}\n"
            )
        elif all_connections:
            logger.info(
                f"Processing SILENT connections (activation relationships were not applied) for node << {node} >> ({source.name}):\n{formatted_silent_connections} "
            )
        elif not all_connections:
            logger.warning(f"No connections found to process in {connections}")

    relationships_map: dict[str, list[dict]] = {
        # Logic checks
        "IF": [],
        # Activations
        "CHECKS": [],
        "ATTEMPTS": [],
        "TRIGGERS": [],
        "DEFAULTS": [],
        "CUTSOFF": [],
        # Definitions
        "ALLOWS": [],
        "PERMITS": [],
        "LOCKS": [],
        "UNLOCKS": [],
        "EXPECTS": [],
        "LISTENS": [],
        "PRIMES": [],
        "UNPRIMES": [],
        "INITIATES": [],
        # Modifications
        "DISABLES": [],
        "DELAYS": [],  # Unused right now but may be in the future
        "APPLIES": [],
        "REVERTS": [],
    }

    for connection in connections:
        relationship = connection["relationship"]
        if relationship in relationships_map:
            relationships_map[relationship].append(connection)

    log_formatted_connections(relationships_map)
    conversation_state.log_conversation_state()

    if cutoff and not relationships_map.get(
        "CUTSOFF"
    ):  # If robeau was cut off, but there are no particular cutsoffs defined
        # TODO Implement a default cutoff message
        pass

    process_logic_relationships(session, relationships_map, conversation_state)

    if not silent:
        end_nodes_reached = process_activation_relationships(
            relationships_map, conversation_state, cutoff
        )
    else:
        end_nodes_reached = []

    process_definitions_relationships(session, relationships_map, conversation_state)
    process_modifications_relationships(session, relationships_map, conversation_state)

    return end_nodes_reached


def handle_transmission_output(
    transmission_node: str, conversation_state: ConversationState
):
    if transmission_node == RESET_EXPECTATIONS:
        conversation_state.reset_attribute("expects")
    elif transmission_node == SET_ROBEAU_UNRESPONSIVE:
        conversation_state.set_state("unresponsive", random.randint(5, 10))
    elif transmission_node == SET_ROBEAU_STUBBORN:
        conversation_state.set_state("stubborn", random.randint(15, 20))
    elif transmission_node == PROLONG_STUBBORN:
        if (
            conversation_state.stubborn["duration"]
            and conversation_state.stubborn["duration"] < 15
        ):
            conversation_state.set_state("stubborn", random.randint(15, 25))
        else:
            logger.info(f"Did not prolong stubborn (duration was long enough)")


def process_node(
    session: Session,
    node: str,
    conversation_state: ConversationState,
    source: QuerySource,
    silent: Optional[bool] = False,
    cutoff: Optional[bool] = False,
    main_call: Optional[bool] = False,
):

    logger.info(
        f"Processing node: << {node} >> from source {source.name}"
        + (" (OG NODE)" if main_call else "")
    )

    connections = get_node_connections(
        session=session,
        text=node,
        conversation_state=conversation_state,
        source=source,
    )

    if not connections:
        logger.info(
            f"No connection obtained for node: << {node} >> from source {source.name}"
        )
        return

    response_nodes_reached = process_relationships(
        session=session,
        connections=connections,
        conversation_state=conversation_state,
        node=node,
        source=source,
        silent=silent,
        cutoff=cutoff,
    )

    for response_node in response_nodes_reached:
        if response_node in transmission_output_nodes:
            handle_transmission_output(response_node, conversation_state)

        if audio_started_event.is_set():
            wait_for_audio_to_play(response_nodes_reached=response_nodes_reached)
        else:
            logger.info("No audio to play, continuing processing")

        process_node(
            session,
            response_node,
            conversation_state,
            ROBEAU,
            cutoff=conversation_state.cutoff,
        )

    logger.info(
        f"End of process for node: << {node} >> from source {source.name}"
        + (" (OG NODE)" if main_call else "")
        + "\n"
    )


def run_update_conversation_state(
    conversation_state: ConversationState,
    session: Session,
    stop_event: threading.Event,
    pause_event: threading.Event,
):
    while not stop_event.is_set():
        if not pause_event.is_set():
            conversation_state.update_conversation_state(session)
        time.sleep(0.5)


def establish_connection():
    start_time = time.time()
    if NEO4J_URI:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    session = driver.session()

    session.run("RETURN 1").consume()  # Warmup query
    connection_time = time.time() - start_time

    print(f"Connection established in {connection_time:.3f} seconds")
    print(driver.get_server_info())
    return driver, session


def initialize():
    driver, session = establish_connection()
    if not driver or not session:
        raise Exception("Failed to establish connection to Neo4j database")
    conversation_state = ConversationState(logger=logger)
    stop_event = threading.Event()
    pause_event = threading.Event()
    update_thread = threading.Thread(
        target=run_update_conversation_state,
        args=(conversation_state, session, stop_event, pause_event),
    )
    update_thread.start()
    return (driver, session, conversation_state, stop_event, update_thread, pause_event)


def cleanup(driver, session, stop_event, update_thread):
    if session:
        session.close()
    if driver:
        driver.close()
    stop_event.set()
    update_thread.join()


def check_for_particular_query(user_query: str):
    force = False
    silent = False

    if "--silent" in user_query:
        silent = True
        user_query = user_query.replace("--silent", "").strip()
    elif "--force" in user_query:
        force = True
        user_query = user_query.replace("--force", "").strip()

    return force, silent, user_query


def launch_specified_query(
    user_query: str,
    query_type: str,
    session: Session,
    conversation_state: ConversationState,
    silent: bool,
):

    global node_thread

    thread_args = {
        "session": session,
        "node": user_query,
        "conversation_state": conversation_state,
        "silent": silent,
        "main_call": True,
    }

    if query_type == "regular":
        node_thread = Thread(
            target=process_node, kwargs={**thread_args, "source": USER}
        )
        node_thread.start()

    elif query_type == "greeting":
        node_thread = Thread(
            target=process_node, kwargs={**thread_args, "source": GREETING}
        )
        node_thread.start()

    elif query_type == "forced":
        """Used for testing to trigger any node without any restrictions"""
        node_thread = Thread(
            target=process_node, kwargs={**thread_args, "source": MODIFIER}
        )
        node_thread.start()


def main():
    (driver, session, conversation_state, stop_event, update_thread, pause_event) = (
        initialize()
    )
    prompt_session: PromptSession = PromptSession()
    global node_thread

    def launch_query(user_query, query_type, silent):
        launch_specified_query(
            user_query=user_query,
            query_type=query_type,
            session=session,
            conversation_state=conversation_state,
            silent=silent,
        )

    try:
        while True:
            with patch_stdout():
                user_query = prompt_session.prompt("Query: ").strip().lower()

                if user_query == "dict":
                    print(conversation_state.__dict__)

                force, silent, user_query = check_for_particular_query(user_query)

                if conversation_state.unresponsive["state"] == True:
                    time_left = conversation_state.unresponsive["time_left"]
                    print(f"Robeau does not listen... time left: {time_left}")
                    continue

                if user_query == "stfu":
                    audio_player.stop_audio()
                    if node_thread:
                        node_thread.join()

                elif node_thread and node_thread.is_alive():
                    print(
                        f"Query refused, processing node: interrupt with << stfu >> if needed"
                    )

                elif force:
                    launch_query(user_query, query_type="forced", silent=silent)

                elif (
                    conversation_state.context["allows"]
                    or conversation_state.context["expects"]
                    or conversation_state.context["listens"]
                ):
                    launch_query(user_query, query_type="regular", silent=silent)

                else:
                    launch_query(user_query, query_type="greeting", silent=silent)

    except Exception as e:
        print(f"Error occurred: {e}")
        logger.exception(e)
    finally:
        cleanup(driver, session, stop_event, update_thread)


if __name__ == "__main__":
    main()

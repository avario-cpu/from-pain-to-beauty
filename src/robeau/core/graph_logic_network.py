import random
import threading
import time
from collections import defaultdict
from logging import Logger
from threading import Thread
from typing import Literal, Optional

import keyboard
from neo4j import GraphDatabase, Result, Session
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from src.robeau.classes.audio_player import AudioPlayer
from src.robeau.core.graph_logic_network_constants import (
    ADMIN,
    ANY_MATCHING_PLEA,
    ANY_MATCHING_PROMPT,
    ANY_MATCHING_WHISPER,
    ANY_NON_SPECIFIC_CUTOFF,
    ANY_RELEVANT_USER_INPUT,
    EXPECTATIONS_FAILURE,
    EXPECTATIONS_SET,
    EXPECTATIONS_SUCCESS,
    GREETING,
    NO_MATCHING_PROMPT,
    PROLONG_STUBBORN,
    RESET_EXPECTATIONS,
    ROBEAU,
    ROBEAU_NO_MORE_STUBBORN,
    SET_ROBEAU_STUBBORN,
    SET_ROBEAU_UNRESPONSIVE,
    STOP_LISTENING_FOR_WHISPERS,
    SYSTEM,
    USER,
    QuerySource,
    transmission_output_nodes,
)
from src.robeau.core.robeau_constants import (
    ROBEAU_RESPONSES_JSON_FILE_PATH as ROBEAU_RESPONSES,
)
from src.utils.helpers import construct_script_name
from src.utils.logging_utils import log_empty_lines, setup_logger

SCRIPT_NAME = construct_script_name(__file__)
logger = setup_logger(SCRIPT_NAME, "DEBUG")


class TypingDetector:
    def __init__(self, pause_event):
        self.pause_event = pause_event
        self.timer = None

    def on_typing_event(self, _event):
        self._set_pause_event()
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(0.7, self._clear_pause_event)
        self.timer.start()

    def _clear_pause_event(self):
        self.pause_event.clear()
        logger.info("Resumed thread updating because user is not typing anymore")

    def _set_pause_event(self):
        if not self.pause_event.is_set():
            logger.info("Paused thread updating because user is typing")
        self.pause_event.set()


class ConversationState:
    def __init__(self, logger_instance: Logger):
        self.logger = logger_instance
        self.lock = threading.Lock()

        # interrupted state
        self.cutoff = False

        # time-bound states
        self.stubborn = {
            "state": False,
            "duration": 0.0,
            "time_left": 0.0,
            "start_time": 0.0,
        }
        self.unresponsive = {
            "state": False,
            "duration": 0.0,
            "time_left": 0.0,
            "start_time": 0.0,
        }

        # Attitude levels
        self.attitude_levels = {"rudeness": 0}

        # Context relationships
        self.context: dict[str, list[dict]] = {
            "allows": [],
            "expects": [],
            "initiates": [],
            "listens": [],
            "locks": [],
            "permits": [],
            "primes": [],
            "unlocks": [],
            "unprimes": [],
        }

        self.listening_context = None

    def _add_item(
        self,
        node: str,
        labels: list[str],
        node_data: dict,
        duration: float | None,
        item_type: str,
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

        if item_type == "listens":
            listening_context = node_data.get("context", None)
            if listening_context:
                self.listening_context = listening_context
                logger.info(f"Set listening context to {self.listening_context}")
            else:
                self.logger.error(f"No listening context found for whisper <{node}>")

        item = {
            "type": item_type,
            "node": node,
            "labels": labels,
            "data": node_data,
            "time_left": duration,
            "duration": duration,
            "start_time": start_time,
        }

        item_list.append(item)
        self.logger.info(f"Added {item_type} <{node}>: {item}")

    def add_item(
        self,
        node: str,
        labels: list[str],
        node_data: dict,
        duration: float | None,
        item_type: str,
    ):
        if item_type in self.context.keys():
            self._add_item(node, labels, node_data, duration, item_type)
        else:
            raise ValueError(
                f"Key from {node} = {item_type} does not match context keys: {self.context.keys()} "
            )

    def delay_item(
        self, node: str, labels: list[str], data: dict, duration: float | None
    ):
        """Unused right now but may be used in the future, Logic wise just know that the difference between this and
        add_initiation is that this is for items that are already in the conversation state, which means a previously
        processed node won't be processed again if they are pointed to with a DELAY relationship
        """
        for item_type, node_list in self.context.items():
            for item in node_list:
                if item["node"] == node:
                    self._add_item(node, labels, data, duration, item_type)

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

    @staticmethod
    def _update_time_left(item: dict):
        current_time = time.time()
        start_time = item["start_time"]
        duration = item["duration"]
        time_left = item["time_left"]

        if time_left is not None:
            elapsed_time = current_time - start_time
            remaining_time = max(0, duration - elapsed_time)
            item["time_left"] = remaining_time

    def _filter_expired_items(self, items: list[dict]) -> tuple[list[dict], list[dict]]:
        valid_items = []
        expired_items = []

        for item in items:
            self._update_time_left(item)
            time_left = item.get("time_left")

            if time_left is None or time_left > 0:
                valid_items.append(item)
            else:
                expired_items.append(item)

        return valid_items, expired_items

    def _handle_initiations(self, expired_items: list[dict], session: Session):
        complete_initiations = [
            item for item in expired_items if item["type"] == "initiates"
        ]

        for initiation in complete_initiations:
            activate_connection_or_item(initiation, self, "item")
            process_node(
                session, initiation["node"], self, source=ROBEAU, main_call=True
            )

    def _remove_expired(
        self, items: list[dict], log_messages: list[str], session: Session, key: str
    ) -> list[dict]:
        valid_items, expired_items = self._filter_expired_items(items)
        self._handle_initiations(expired_items, session)

        for item in valid_items:
            item_type = item.get("type")
            node = item.get("node")
            labels = item.get("labels", [])
            time_left = item.get("time_left")

            if time_left is not None:
                log_messages.append(
                    f"{item_type}: {labels}: <{node}> ({time_left:.2f}): {item}"
                )

        items_after_initiations = self.context[key]
        valid_items = [
            item for item in items_after_initiations if item not in expired_items
        ]

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
                    handle_transmission_input(session, ROBEAU_NO_MORE_STUBBORN, self)

            setattr(self, state, state_obj)

    def _update_attitude_levels(self, log_messages: list[str]):
        for attitude, level in self.attitude_levels.items():
            if level > 0 and random.randint(0, 9) == 0:
                level -= 1
                log_messages.append(f"{attitude}: level decreased to {level}")

    def update_conversation_state(self, session: Session):
        log_messages: list[str] = []

        self._update_timed_items(session, log_messages)
        self._update_timed_states(session, log_messages)
        self._update_attitude_levels(log_messages)

        if log_messages:
            self.logger.info("Time-bound updates:\n" + "\n".join(log_messages))
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
            source=ADMIN,
            conversation_state=self,
            silent=True,
        )

    def revert_definitions(self, session: Session, node: str):
        definitions_to_revert = (
            get_node_connections(
                session, text=node, source=ADMIN, conversation_state=self
            )
            or []
        )
        formatted_definitions = [
            (i["start_node"], i["relationship"], i["end_node"])
            for i in definitions_to_revert
        ]
        self.logger.info(f"Obtained definitions to revert: {formatted_definitions}")

        for connection in definitions_to_revert:
            relationship = connection.get("relationship", "").lower()
            node = connection.get("end_node", "")
            self._revert_individual_definition(relationship, node)

    def _revert_individual_definition(self, relationship: str, node: str):
        for definition_type, definitions_list in self.context.items():
            initial_count = len(definitions_list)
            definitions_list[:] = [
                definition
                for definition in definitions_list
                if not (
                    definition["type"] == relationship and definition["node"] == node
                )
            ]
            if len(definitions_list) < initial_count:
                self.logger.info(f"Removed {definition_type}: <{node}>")

    def log_conversation_state(self):
        log_message = []

        states = {"stubborn": self.stubborn, "unresponsive": self.unresponsive}

        if (
            not any(self.context.values())
            and not any(state["state"] for state in states.values())
            and not any(value for value in self.attitude_levels.values())
        ):
            log_message.append("No items in conversation state")
        else:
            log_message.append("Conversation state:")

        context_messages = []
        for item_type, items in self.context.items():
            for item in items:
                node = item["node"]
                context_messages.append(f"Context {item_type}: <{node}>: {item}")

        state_messages = []
        for state_name, state in states.items():
            if state["state"]:
                state_messages.append(f"State {state_name} : {state}")

        attitude_messages = []
        for attitude, level in self.attitude_levels.items():
            if level > 0:
                attitude_messages.append(f"Attitude {attitude} level: {level}")

        listening_context_message = {f"Listening context: {self.listening_context}"}

        log_message.extend(sorted(context_messages))
        log_message.extend(sorted(state_messages))
        log_message.extend(sorted(attitude_messages))
        log_message.extend(listening_context_message)

        self.logger.info("\n".join(log_message))


audio_player = AudioPlayer(ROBEAU_RESPONSES, logger=logger)

processing_nodes_audio = threading.Event()
audio_player_first_callback = threading.Event()
audio_started_event = threading.Event()
robeau_is_talking = threading.Event()
audio_finished_event = threading.Event()

node_thread: Thread | None = None


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
        stubborn = conversation_state.stubborn
        if stubborn["state"] and stubborn["time_left"] < 10:
            conversation_state.set_state("stubborn", random.randint(10, 15))
        else:
            logger.info(
                f"Did not prolong stubborn (time_left {stubborn["time_left"]:.2f} was long enough)"
            )
    elif transmission_node == STOP_LISTENING_FOR_WHISPERS:
        conversation_state.context["listens"] = []
        logger.info("Cleared the listened to whispers list")  # Keep the context set.


def reset_audio_events():
    audio_finished_event.clear()
    audio_started_event.clear()
    audio_player_first_callback.clear()
    robeau_is_talking.clear()


def interrupt_robeau():
    audio_player.stop_audio()
    if node_thread:
        node_thread.join()


def wait_for_audio_management(response_nodes_reached: list[str]):
    logger.info("Waiting for initial callback from audio_player")
    audio_player_first_callback.wait()
    audio_player_first_callback.clear()
    logger.info("Callback received from audio_player, proceeding")

    if audio_started_event.is_set():
        logger.info(
            f"Stopping to wait for audio to play for nodes: {response_nodes_reached}, "
            f"state of audio finished event: {audio_finished_event}"
        )
        audio_finished_event.wait()
        reset_audio_events()
        logger.info(
            f"Finished waiting for audio to play for nodes: {response_nodes_reached}"
        )
    else:
        logger.info(
            f"No audio to play for nodes: {response_nodes_reached} continuing processing"
        )

    processing_nodes_audio.clear()


def play_audio(
    node: str,
    conversation_state: ConversationState,
    multiple_activations: Optional[int] = False,
):
    def on_start():
        audio_started_event.set()
        audio_player_first_callback.set()
        robeau_is_talking.set()
        conversation_state.cutoff = False

    def on_stop():
        audio_finished_event.set()
        conversation_state.cutoff = True

    def on_end():
        audio_finished_event.set()

    def on_error():
        audio_player_first_callback.set()
        audio_finished_event.set()
        conversation_state.cutoff = False

    audio_player.set_callbacks(
        on_start=on_start,
        on_stop=on_stop,
        on_end=on_end,
        on_error=on_error,
    )

    processing_nodes_audio.set()
    audio_player.play_audio(node, multiple_activations)


def process_node_data(data: dict, conversation_state: ConversationState):
    for attitude, level in conversation_state.attitude_levels.items():
        if data.get(attitude + "LevelIncrease"):
            new_level = level + data[attitude + "LevelIncrease"]
            if new_level > 100:
                new_level = 100

            conversation_state.attitude_levels[attitude] = new_level

            logger.info(
                f"{attitude} level increased to {conversation_state.attitude_levels[attitude]}"
            )


def activate_connection_or_item(
    node_dict: dict,
    conversation_state: ConversationState,
    dict_type: Literal["connection", "item"],
    multiple_activations: Optional[int] = False,
):
    """Works for both activation connections (end_node) and dictionaries from the conversation state(node)."""

    if dict_type == "connection":
        node = node_dict.get("end_node", "")
        labels = node_dict.get("labels", {}).get("end", "")
        data = node_dict.get("data", {}).get("end", {})

    elif dict_type == "item":
        node = node_dict.get("node", "")
        labels = node_dict.get("labels", "")
        data = node_dict.get("data", {})

    if data:
        process_node_data(data, conversation_state)

    vocal_labels = ["Response", "Question", "Test"]

    if any(label in vocal_labels for label in labels):
        play_audio(node, conversation_state, multiple_activations)
        print(node)
    else:
        logger.info(f" <{node}> with labels {labels} is not considered an audio output")
        print(f"-{node}")  # - is to indicate that the node is not an audio output

    return node_dict


def activate_connections(
    connections: list[dict],
    conversation_state: ConversationState,
    connection_type: Literal["regular", "random", "logic_gate"],
):
    conn_names = [
        f"{', '.join(list(connection.values())[0:3])}" for connection in connections
    ]

    if len(conn_names) > 0:
        logger.info(
            f"Activating {len(connections)} {connection_type} connection(s): {conn_names}"
        )
    for connection in connections:
        activate_connection_or_item(
            connection,
            conversation_state,
            "connection",
            multiple_activations=len(connections) if len(connections) > 1 else False,
        )
    return connections


def additional_conditions_are_true(
    connections: list[tuple[dict, bool, str]], conversation_state: ConversationState
):
    for connection in connections:
        conn, is_true, attribute = connection
        context = conversation_state.context[attribute]

        if is_true:
            if not any(conn["end_node"] == item["node"] for item in context):
                return False
        else:
            if any(conn["end_node"] == item["node"] for item in context):
                return False
    return True


def initial_condition_is_true(
    connection: tuple[dict, bool, str], conversation_state: ConversationState
):
    conn, is_true, attribute = connection
    context = conversation_state.context[attribute]
    if is_true:
        return any(conn["end_node"] == item["node"] for item in context)
    else:
        return not any(conn["end_node"] == item["node"] for item in context)


def filter_logic_connections(
    attribute_map: dict, connections: list[dict], logic_gate: str
) -> tuple[tuple[dict, bool, str] | None, list[tuple[dict, bool, str]], list[dict]]:
    is_conditions = {"IS_" + key: attr for key, attr in attribute_map.items()}
    and_is_conditions = {"AND_IS_" + key: attr for key, attr in attribute_map.items()}

    is_not_conditions = {"IS_NOT_" + key: attr for key, attr in attribute_map.items()}
    and_is_not_conditions = {
        "AND_IS_NOT_" + key: attr for key, attr in attribute_map.items()
    }

    initial_conn: tuple[dict, bool, str] | None = None
    and_conns: list[tuple[dict, bool, str]] = []
    then_conns: list[dict] = []

    for conn in connections:
        relationship = conn["relationship"]

        if relationship in is_conditions:
            initial_conn = (conn, True, is_conditions[relationship])

        elif relationship in is_not_conditions:
            initial_conn = (conn, False, is_not_conditions[relationship])

        elif relationship in and_is_conditions:
            and_conns.append((conn, True, and_is_conditions[relationship]))

        elif relationship in and_is_not_conditions:
            and_conns.append((conn, False, and_is_not_conditions[relationship]))

        elif relationship == "THEN":
            then_conns.append(conn)
        else:
            logger.warning(f"Atypical connection for logicGate <{logic_gate}>: {conn}")

    if not initial_conn:
        logger.error(f"No initial connection found for LogicGate: <{logic_gate}>")

    if not then_conns:
        logger.error(f'No "THEN" connection found for LogicGate: <{logic_gate}>')

    formatted_and_conns = "\nAnd: ".join([str(and_conn) for and_conn in and_conns])
    formatted_then_conns = "\nThen: ".join([str(then_conn) for then_conn in then_conns])

    logger.info(
        f"LogicGate <{logic_gate}> connections: \nInitial: {initial_conn} "
        f"\nAnd: {formatted_and_conns} \nThen: {formatted_then_conns}"
    )
    return initial_conn, and_conns, then_conns


def process_logic_connections(
    connections: list[dict],
    logic_gate: str,
    conversation_state: ConversationState,
) -> list[dict]:
    attribute_map = {
        "ALLOWED": "allows",
        "PERMITTED": "permits",
        "LOCKED": "locks",
        "UNLOCKED": "unlocks",
        "EXPECTED": "expects",
        "PRIMED": "primes",
        "UNPRIMED": "unprimes",
        "LISTENED": "listens",
        "INITIATED": "initiates",
    }

    initial_conn, and_conns, then_conns = filter_logic_connections(
        attribute_map, connections, logic_gate
    )

    if not initial_conn or not then_conns:
        return []

    if not initial_condition_is_true(initial_conn, conversation_state):
        return []

    if and_conns and not additional_conditions_are_true(and_conns, conversation_state):
        return []

    activated_connections = activate_connections(
        then_conns, conversation_state, "logic_gate"
    )

    return activated_connections


def process_logic_relationships(
    session: Session, relations_map: dict, conversation_state: ConversationState
) -> list[str]:
    if not relations_map.get("IF"):
        return []

    end_nodes_reached = []

    for if_connection in relations_map["IF"]:
        logic_gate = if_connection["end_node"]
        gate_connections = get_node_connections(
            session, logic_gate, conversation_state, ROBEAU
        )

        if not gate_connections:
            logger.info(f"No connections found for LogicGate: {logic_gate}")
            continue

        activated_connections = process_logic_connections(
            gate_connections, logic_gate, conversation_state
        )

        if not activated_connections:
            logger.info(f"No connections activated for LogicGate: {logic_gate}")

        end_nodes_reached = (
            [connection["end_node"] for connection in activated_connections]
            if activated_connections
            else []
        )
    return end_nodes_reached


def process_modifications_connections(
    session: Session,
    connections: list[dict],
    process_method,
):
    for connection in connections:
        end_node = connection.get("end_node", "")
        labels = connection.get("labels", {}).get("end", [])
        data = connection.get("data", {}).get("end", {})
        duration = connection.get("params", {}).get("duration")
        process_method(end_node, labels, data, duration, session)


def process_modifications_relationships(
    session: Session,
    relationships_map: dict[str, list[dict]],
    conversation_state: ConversationState,
):
    relationship_methods = {
        "DELAYS": lambda end_node,
        labels,
        data,
        duration,
        session: conversation_state.delay_item(
            end_node, labels, data, duration
        ),  # Unused right now but may be used in the future
        "DISABLES": lambda end_node,
        labels,
        data,
        duration,
        session: conversation_state.disable_item(end_node),
        "APPLIES": lambda end_node,
        labels,
        data,
        duration,
        session: conversation_state.apply_definitions(session, end_node),
        "REVERTS": lambda end_node,
        labels,
        data,
        duration,
        session: conversation_state.revert_definitions(session, end_node),
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
                data = connection.get("data", {}).get("end", {})
                if not node:
                    logger.error(f"No end node for connection {connection}")
                    continue
                conversation_state.add_item(
                    node=node,
                    labels=labels,
                    node_data=data,
                    duration=duration,
                    item_type=relationship_lower,
                )

    if relationships_map["EXPECTS"]:
        handle_transmission_input(session, EXPECTATIONS_SET, conversation_state)


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
        logger.info(f"Selected end_node for random pool Id {pool_id} is: <{end_node}>")
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
    activate_connections(
        selected_connections, conversation_state, connection_type="random"
    )
    return selected_connections


def execute_attempt(
    connection: dict,
    node: str,
    conversation_state: ConversationState,
) -> bool:
    if any(
        node == item["node"] for item in conversation_state.context["unlocks"]
    ) or any(node == item["node"] for item in conversation_state.context["primes"]):
        logger.info(
            f"Successful attempt at connection: {list(connection.values())[0:3]}"
        )
        return True
    else:
        logger.info(f"Failed attempt at connection: {list(connection.values())[0:3]}")
    return False


def node_is_inaccessible(
    node: str, connection: dict, conversation_state: ConversationState
) -> bool:
    connection_locked = any(
        node == item["node"] for item in conversation_state.context["locks"]
    )
    connection_unprimed = any(
        node == item["node"] for item in conversation_state.context["unprimes"]
    )

    if connection_locked:
        logger.info(f"Connection is locked: {list(connection.values())[0:3]}")
    if connection_unprimed:
        logger.info(f"Connection is unprimed: {list(connection.values())[0:3]}")

    return connection_locked or connection_unprimed


def evaluation_meets_criteria(
    connection: dict, conversation_state: ConversationState
) -> bool:
    def assign_default_min():
        logger.info("No min value found for evaluation, defaulting to 0")
        return 0

    def assign_default_max():
        logger.info("No max value found for evaluation, defaulting to 100")
        return 100

    for attitude, level in conversation_state.attitude_levels.items():
        eval_min = (
            connection.get("params", {}).get(attitude + "LevelMin")
            or assign_default_min()
        )
        eval_max = (
            connection.get("params", {}).get(attitude + "LevelMax")
            or assign_default_max()
        )

        # ! important to note that the evaluation is inclusive

        if eval_min <= level <= eval_max:
            logger.info(
                f"Connection meets criteria: {list(connection.values())[0:3]} "
                f"(min {eval_min} <= {attitude}: {level} <= max {eval_max})"
            )
            return True
        else:
            logger.info(
                f"Connection does not meet criteria: {list(connection.values())[0:3]} "
                f"(min {eval_min} <= {attitude}: {level} <= max {eval_max})"
            )
            return False

    return False


def process_activation_connections(
    connections: list[dict],
    conversation_state: ConversationState,
    connection_type: str,
    reset_primes: Optional[bool] = True,
) -> list[dict]:
    random_connections = []
    regular_connections = []
    activated_connections = []

    for connection in connections:
        node = connection["end_node"]
        if node_is_inaccessible(node, connection, conversation_state):
            continue

        if connection_type == "EVALUATES" and not evaluation_meets_criteria(
            connection, conversation_state
        ):
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
            regular_connections, conversation_state, connection_type="regular"
        )
    )

    if activated_connections and reset_primes:
        conversation_state.reset_attribute("primes", "unprimes")

    return activated_connections


def process_activation_relationships(
    relationships_map: dict[str, list[dict]],
    conversation_state: ConversationState,
    cutoff: Optional[bool] = False,
) -> list[str]:
    priority_order = ["CHECKS", "EVALUATES", "ATTEMPTS", "TRIGGERS", "DEFAULTS"]
    end_nodes_reached = []

    # Always process all ACTIVATES
    if relationships_map["ACTIVATES"]:
        activated_connections = process_activation_connections(
            relationships_map["ACTIVATES"],
            conversation_state,
            connection_type="ACTIVATES",
            reset_primes=False,
        )
        if activated_connections:
            end_nodes_reached.extend(
                [item["end_node"] for item in activated_connections]
            )

    if cutoff:
        priority_order = ["CUTSOFF"] + priority_order

    for key in priority_order:
        if relationships_map[key]:
            activated_connections = process_activation_connections(
                relationships_map[key],
                conversation_state,
                connection_type=key,
            )
            if activated_connections:
                end_nodes_reached.extend(
                    [item["end_node"] for item in activated_connections]
                )
                break  # Stop processing further as we've found the first activated
                # connections

    return end_nodes_reached


def process_special_relationships(session, relationships_map, conversation_state):
    if relationships_map["REPLACES"]:
        replacing_node = relationships_map["REPLACES"][0]["start_node"]
        replaced_node = relationships_map["REPLACES"][0]["end_node"]
        logger.info(
            f"<{replacing_node}> will now be processed as if it was <{replaced_node}>"
        )
        process_node(
            session,
            replaced_node,
            conversation_state,
            source=ADMIN,  # assures access to the node after the context switch in between the two nodes activation
        )


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
        conns_from_map = []
        cutoff_status = "(cutoff)" if cutoff else ""
        for connection in relationships_map.values():
            conns_from_map.extend(connection)

        formatted_connections = "\n".join(
            [str(connection) for connection in connections]
        )
        formatted_silent_connections = "\n".join(
            [
                str(connection)
                for connection in connections
                if connection["relationship"]
                not in ("CHECKS", "ATTEMPTS", "TRIGGERS", "DEFAULTS", "CUTSOFF")
            ]
        )
        if silent and conns_from_map:
            logger.info(
                f"Processing SILENT connections {cutoff_status} (activation relationships were not applied) "
                f"for node <{node}> ({source.name}):\n{formatted_silent_connections}"
            )
        elif conns_from_map:
            logger.info(
                f"Processing connections for node <{node}> from source "
                f"{source.name} {cutoff_status}:\n{formatted_connections}"
            )
        elif not conns_from_map:
            logger.warning(
                f"No connections found to process in: \n{formatted_connections}\n "
                f"Must not be bound to a valid key in the relationships_map"
            )

    relationships_map: dict[str, list[dict]] = {
        # Special
        "REPLACES": [],
        # Logic checks
        "IF": [],
        # Activations
        "ACTIVATES": [],
        "CHECKS": [],
        "EVALUATES": [],
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

    conversation_state.log_conversation_state()

    log_formatted_connections(relationships_map)
    end_nodes_reached = []

    if cutoff and not relationships_map["CUTSOFF"]:
        handle_transmission_input(session, ANY_NON_SPECIFIC_CUTOFF, conversation_state)

    process_special_relationships(session, relationships_map, conversation_state)

    if not silent:
        end_nodes_reached.extend(
            process_logic_relationships(session, relationships_map, conversation_state)
        )
        end_nodes_reached.extend(
            process_activation_relationships(
                relationships_map, conversation_state, cutoff
            )
        )

    process_definitions_relationships(session, relationships_map, conversation_state)
    process_modifications_relationships(session, relationships_map, conversation_state)

    return end_nodes_reached


def handle_transmission_input(
    session: Session,
    transmission_node: str,
    conversation_state: ConversationState,
):
    process_node(
        session, transmission_node, conversation_state, SYSTEM, input_node=True
    )


def query_database(
    session: Session,
    text: str,
    labels: list[str],
    conversation_state: "ConversationState",
) -> Optional[Result]:
    queries = []

    for label in labels:
        if label == "Whisper":
            listening_context = conversation_state.listening_context

            if listening_context:
                queries.append(
                    f"""
                    MATCH (x:{label})-[r]->(y)
                    WHERE x.context = $listening_context
                    AND toLower(x.text) = toLower($text)
                    RETURN x, r, y
                    """
                )
            else:
                logger.warning(f"Listening context is not set for Whisper: {text}")
        else:
            queries.append(
                f"""
                MATCH (x:{label})-[r]->(y)
                WHERE toLower(x.text) = toLower($text)
                RETURN x, r, y
                """
            )

    if not queries:
        logger.warning("No queries were constructed. Check the labels or context.")
        return None

    full_query = "\nUNION\n".join(queries)
    # noinspection PyTypeChecker
    result = session.run(
        full_query, text=text, listening_context=conversation_state.listening_context
    )

    return result if result.peek() else None


def prompt_matches_allows(
    session: Session, text: str, conversation_state: ConversationState
) -> bool:
    if any(
        text.lower() == item["node"].lower()
        for item in conversation_state.context["allows"]
    ):
        handle_transmission_input(session, ANY_MATCHING_PROMPT, conversation_state)
        return True
    return False


def prompt_matches_listens(
    session: Session, text: str, conversation_state: ConversationState
) -> bool:
    if any(
        text.lower() == item["node"].lower()
        for item in conversation_state.context["listens"]
    ):
        handle_transmission_input(session, ANY_MATCHING_WHISPER, conversation_state)
        return True
    return False


def prompt_matches_permits(
    session: Session, text: str, conversation_state: ConversationState
) -> bool:
    if any(
        text.lower() == item["node"].lower()
        for item in conversation_state.context["permits"]
    ):
        handle_transmission_input(session, ANY_MATCHING_PLEA, conversation_state)
        return True
    return False


def prompt_is_not_understood(session: Session, conversation_state: ConversationState):
    handle_transmission_input(session, NO_MATCHING_PROMPT, conversation_state)


def conduct_prompt_matching(
    session: Session,
    text: str,
    conversation_state: ConversationState,
    labels: list[str],
) -> list[str]:
    matched = False

    if prompt_matches_listens(session, text, conversation_state):
        labels.append("Whisper")
        matched = True

    if prompt_matches_permits(session, text, conversation_state):
        labels.append("Plea")
        matched = True

    if prompt_matches_allows(session, text, conversation_state):
        if conversation_state.stubborn["state"]:
            pass  # no prompt matching when stubborn
        else:
            labels.append("Prompt")
        matched = True

    if not matched:
        if conversation_state.stubborn["state"]:
            logger.debug("Stubborn context: Did not understand")
            prompt_is_not_understood(session, conversation_state)

        elif conversation_state.context["allows"]:
            logger.debug("Normal context: Did not understand")
            prompt_is_not_understood(session, conversation_state)

    return labels


def prompt_meets_expectations(
    session: Session, text: str, conversation_state: ConversationState
) -> bool:
    if any(
        text.lower() == item["node"].lower()
        for item in conversation_state.context["expects"]
    ):
        logger.info(f"<{text}> meets conversation expectations")
        handle_transmission_input(session, EXPECTATIONS_SUCCESS, conversation_state)
        return True
    else:
        logger.info(f"<{text}> does not meet conversation expectations")
        handle_transmission_input(session, EXPECTATIONS_FAILURE, conversation_state)
        return False


def check_for_any_relevant_user_input(
    session: Session, text: str, conversation_state: ConversationState
):
    def text_in_conversation_context() -> bool:
        return any(
            text.lower() == dictionary["node"].lower()
            for list_of_dicts in conversation_state.context.values()
            for dictionary in list_of_dicts
        )

    if text_in_conversation_context():
        handle_transmission_input(session, ANY_RELEVANT_USER_INPUT, conversation_state)


def handle_user_input_labelling(
    session: Session,
    text: str,
    conversation_state: ConversationState,
    labels: list[str],
):
    check_for_any_relevant_user_input(session, text, conversation_state)

    if conversation_state.context["expects"] and prompt_meets_expectations(
        session, text, conversation_state
    ):
        labels.append("Answer")
        return labels

    else:
        labels = conduct_prompt_matching(session, text, conversation_state, labels)

    return labels


def define_labels(
    session: Session,
    text: str,
    conversation_state: ConversationState,
    source: QuerySource,
) -> list[str]:
    labels: list[str] = []

    if source == USER:
        labels = handle_user_input_labelling(session, text, conversation_state, labels)
        return labels

    elif source == GREETING:
        labels.append("Greeting")

    elif source == ROBEAU:
        labels.extend(
            [
                "Response",
                "Question",
                "LogicGate",
                "Greeting",
                "Output",
                "TrafficGate",
                "Input",
            ]
        )

    elif source == SYSTEM:
        labels.append("Input")

    elif source == ADMIN:
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

    return labels


def get_node_connections(
    session: Session,
    text: str,
    conversation_state: ConversationState,
    source: QuerySource,
) -> list[dict] | None:
    labels = define_labels(session, text, conversation_state, source)

    if not labels:
        labels = [
            "None"
        ]  # This will not return results from the database, but it will also not throw
        # an error. We still want to call get_node_data (instead of making an early
        # return) in order to call relevant nested functions inside.

    logger.info(f"Labels for fetching <{text}> connection are {labels}")

    result = query_database(session, text, labels, conversation_state)

    if not result:
        return None

    result_data = [
        {
            "start_node": dict(record["x"])["text"],
            "relationship": record["r"].type,
            "end_node": dict(record["y"])["text"],
            "params": dict(record["r"]),
            "labels": {
                "start": list(record["x"].labels),
                "end": list(record["y"].labels),
            },
            "data": {
                "start": {k: v for k, v in dict(record["x"]).items() if k != "text"},
                "end": {k: v for k, v in dict(record["y"]).items() if k != "text"},
            },
        }
        for record in result
    ]

    return result_data


def process_node(
    session: Session,
    node: str,
    conversation_state: ConversationState,
    source: QuerySource,
    silent: Optional[bool] = False,
    cutoff: Optional[bool] = False,
    main_call: Optional[bool] = False,
    initiated: Optional[bool] = False,
    input_node: Optional[bool] = False,
):
    log_empty_lines(logger=logger, lines=7 if main_call else 0)

    if input_node:
        logger.info(f">>> Start of intermediary input process for: <{node}>")

    logger.info(
        f"Processing node: <{node}> from source {source.name}"
        + (" (OG)" if main_call else "")
        + (" (cutoff)" if cutoff else "")
        + ("(initiation)" if initiated else "")
    )

    connections = get_node_connections(
        session=session,
        text=node,
        conversation_state=conversation_state,
        source=source,
    )

    if not connections:
        logger.info(
            f"No connection obtained for node: <{node}> from source {source.name}"
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

        if processing_nodes_audio.is_set():
            wait_for_audio_management(response_nodes_reached=response_nodes_reached)

        log_empty_lines(logger=logger, lines=1)
        logger.info("Next node in the chain...\n")

        process_node(
            session,
            response_node,
            conversation_state,
            ROBEAU,
            cutoff=conversation_state.cutoff,
        )

    logger.info(
        f"End of process for node: <{node}> from source {source.name}"
        + (" (OG)" if main_call else "")
    )

    if input_node:
        logger.info(f">>> End of intermediary process for input <{node}>\n\n\n")

    log_empty_lines(logger=logger, lines=7 if main_call else 0)


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


def robeau_is_listening(conversation_state: ConversationState):
    if (
        conversation_state.context["allows"]
        or conversation_state.context["permits"]
        or conversation_state.context["expects"]
        or conversation_state.context["listens"]
    ):
        return True


def establish_connection():
    start_time = time.time()
    if NEO4J_URI:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    else:
        raise ConnectionError("Failed to establish connection to Neo4j database")

    session = driver.session()

    session.run("RETURN 1").consume()  # Warmup query
    connection_time = time.time() - start_time

    print(f"Connection established in {connection_time:.3f} seconds")
    print(driver.get_server_info())
    return driver, session


def initialize():
    driver, session = establish_connection()
    if not driver or not session:
        raise ConnectionError("Failed to establish connection to Neo4j database")
    conversation_state = ConversationState(logger_instance=logger)
    stop_event = threading.Event()
    pause_event = threading.Event()
    update_thread = threading.Thread(
        target=run_update_conversation_state,
        args=(conversation_state, session, stop_event, pause_event),
    )
    update_thread.start()

    return (
        driver,
        session,
        conversation_state,
        stop_event,
        update_thread,
        pause_event,
    )


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
    query_type: Literal["regular", "greeting", "forced"],
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
        # Used for testing to trigger any node without any restrictions
        upper_node = str(thread_args["node"]).upper()
        if upper_node in transmission_output_nodes:
            logger.info(
                f"treating node {upper_node} from forced query as a transmission output"
            )
            handle_transmission_output(upper_node, conversation_state)

        node_thread = Thread(
            target=process_node, kwargs={**thread_args, "source": ADMIN}
        )
        node_thread.start()


def launch_query(user_query, query_type, silent, session, conversation_state):
    launch_specified_query(
        user_query=user_query,
        query_type=query_type,
        session=session,
        conversation_state=conversation_state,
        silent=silent,
    )


def handle_user_query(prompt_session, conversation_state, session):
    if prompt_session:
        # noinspection PyArgumentList
        with patch_stdout():
            user_query = prompt_session.prompt("Query: ").strip().lower()
    else:
        user_query = input("Query: ").strip().lower()

    if user_query == "dict":
        print(conversation_state.__dict__)

    force, silent, user_query = check_for_particular_query(user_query)

    if conversation_state.unresponsive["state"]:
        time_left = conversation_state.unresponsive["time_left"]
        print(f"Robeau does not listen... time left: {time_left}")
        return

    if user_query == "stfu":
        interrupt_robeau()

    elif node_thread and node_thread.is_alive():
        print("Query refused, processing node: interrupt with <stfu> if needed")

    elif force:
        launch_query(user_query, "forced", silent, session, conversation_state)

    elif robeau_is_listening(conversation_state):
        launch_query(user_query, "regular", silent, session, conversation_state)

    else:
        launch_query(user_query, "greeting", silent, session, conversation_state)


def main_loop(prompt_session, conversation_state, session):
    try:
        while True:
            handle_user_query(prompt_session, conversation_state, session)
    except Exception as e:
        print(f"Error occurred: {e}")
        logger.exception(e)


def setup_typing_detector(pause_event):
    typing_detector = TypingDetector(pause_event)
    keyboard.on_press(typing_detector.on_typing_event)
    return typing_detector


def create_prompt_session():
    try:
        return PromptSession()
    except Exception as e:
        print(f"Caught exception: {e}")
        print(
            """
            Failed to create PromptSession: Running from an IDE ?\n
            Expect weird behavior in the input prompt when typing while a thread prints at the same time.\n
            Program is better off run from the terminal, everything should still work though."""
        )
        logger.warning(e)
        return


def main():
    driver, session, conversation_state, stop_event, update_thread, pause_event = (
        initialize()
    )

    try:
        prompt_session = create_prompt_session()
        setup_typing_detector(pause_event)
        main_loop(prompt_session, conversation_state, session)
    finally:
        cleanup(driver, session, stop_event, update_thread)
        keyboard.unhook_all()


if __name__ == "__main__":
    main()

import random
import threading
import time
from collections import defaultdict
from logging import DEBUG, INFO, Logger
from threading import Thread
from typing import Optional

from neo4j import GraphDatabase, Result, Session
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from src.robeau.classes.audio_player import AudioPlayer
from src.robeau.classes.graph_logic_constants import (
    ANY_MATCHING_PROMPT_OR_WHISPER,
    EXPECTATIONS_FAILURE,
    EXPECTATIONS_SET,
    EXPECTATIONS_SUCCESS,
    GREETING,
    MODIFIER,
    NO_MATCHING_PROMPT_OR_WHISPER,
    RESET_EXPECTATIONS,
    ROBEAU,
    SYSTEM,
    USER,
    QuerySource,
    transmissions_output_aliases,
)
from src.robeau.core.constants import AUDIO_MAPPINGS_FILE_PATH
from src.utils.helpers import construct_script_name, setup_logger

SCRIPT_NAME = construct_script_name(__file__)
logger = setup_logger(SCRIPT_NAME, level=DEBUG)


class ConversationState:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.cutoff = False
        # definitions items
        self.allows: list[dict] = []
        self.locks: list[dict] = []
        self.unlocks: list[dict] = []
        self.expects: list[dict] = []
        self.primes: list[dict] = []
        self.listens: list[dict] = []
        # activations items
        self.initiates: list[dict] = []

    def _add_item(
        self,
        node: str,
        node_labels: list[str],
        duration: float | None,
        item_list: list,
        item_type: str,
    ):
        start_time = time.time()

        for existing_item in item_list:
            if existing_item["node"] == node:
                if duration is None:  # None means infinite duration here
                    return

                # Refresh duration if the item already exists
                existing_item["duration"] = duration
                existing_item["timeLeft"] = duration
                existing_item["start_time"] = start_time
                self.logger.info(f"Refreshed the time duration of {existing_item}")
                return

        item_list.append(
            {
                "type": item_type,
                "node": node,
                "labels": node_labels,
                "timeLeft": duration,
                "duration": duration,
                "start_time": start_time,
            }
        )

    def add_allows(self, node: str, labels: list[str], duration: float | None):
        self._add_item(node, labels, duration, self.allows, "allows")

    def add_unlocks(self, node: str, labels: list[str], duration: float | None):
        self._add_item(node, labels, duration, self.unlocks, "unlocks")

    def add_locks(self, node: str, labels: list[str], duration: float | None):
        self._add_item(node, labels, duration, self.locks, "locks")

    def add_expects(self, node: str, labels: list[str], duration: float | None):
        self._add_item(node, labels, duration, self.expects, "expects")

    def add_primes(self, node: str, labels: list[str], duration: float | None):
        self._add_item(node, labels, duration, self.primes, "primes")

    def add_listens(self, node: str, labels: list[str], duration: float | None):
        self._add_item(node, labels, duration, self.listens, "listens")

    def add_initiates(self, node: str, labels: list[str], duration: float | None):
        self._add_item(node, labels, duration, self.initiates, "initiates")

    def delay_item(self, node: str, labels: list[str], duration: float | None):
        """Unused right now but may be used in the future, Logic wise just know that the difference between this and add_initiation is that this is for items that are already in the conversation state, which means a previously processed node wont be processed again if they are pointed to with a DELAY relationship"""
        for node_list in [self.locks, self.unlocks, self.expects, self.primes]:
            for item in node_list:
                if item["node"] == node:
                    self._add_item(node, labels, duration, node_list, item["type"])

    def disable_item(self, node: str):
        for node_list in [self.primes, self.initiates, self.listens]:
            for item in node_list:
                if item["node"] == node:
                    node_list.remove(item)
                    self.logger.info(f"Item disabled: {item}")
                    return

    def _update_time_left(self, item: dict):
        current_time = time.time()
        start_time = item["start_time"]
        duration = item["duration"]
        time_left = item.get("timeLeft")

        if time_left is not None:
            elapsed_time = current_time - start_time
            remaining_time = max(0, duration - elapsed_time)
            item["timeLeft"] = remaining_time

    def _remove_expired(
        self, items: list, log_messages: list, session: Session
    ) -> list:
        valid_items = []
        complete_initiations = []

        for item in items:
            self._update_time_left(item)
            time_left = item.get("timeLeft")
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
                if item_type == "initiates":
                    complete_initiations.append(item)
                    self.logger.info(f"Initiation complete: {item}")
                else:
                    self.logger.info(f"Item {item_type} has expired: {item}")

        if complete_initiations:
            for initiation in complete_initiations:
                activate_connection_or_item(initiation, self)
                process_node(session, initiation["node"], self, source=ROBEAU)

        return valid_items

    def update_timed_items(self, session: "Session"):
        items_to_update = [
            "allows",
            "locks",
            "unlocks",
            "expects",
            "primes",
            "listens",
            "initiates",
        ]
        log_messages: list[str] = []

        for item in items_to_update:
            updated_items = self._remove_expired(
                getattr(self, item), log_messages, session
            )
            setattr(self, item, updated_items)

        if log_messages:
            self.logger.info(
                "Time-bound items update:\n" + "\n".join(log_messages) + "\n"
            )
        else:
            self.logger.info("No time-bound items to update")

    def reset_attribute(self, attribute: str):
        valid_attributes = [
            "locks",
            "unlocks",
            "primes",
            "expects",
            "listens",
            "initiates",
        ]

        if attribute in valid_attributes:
            if getattr(self, attribute, None):
                setattr(self, attribute, [])
                self.logger.info(f"Reset attribute: {attribute}")
        else:
            self.logger.error(f"Invalid attribute: {attribute}")

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
                session=session,
                text=node,
                source=MODIFIER,
                conversation_state=self,
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

            self._revert_individual_definition("locks", end_node, self.locks)
            self._revert_individual_definition("unlocks", end_node, self.unlocks)
            self._revert_individual_definition("allows", end_node, self.allows)

    def _revert_individual_definition(
        self, definition_type: str, node: str, definitions: list[dict]
    ):
        initial_count = len(definitions)
        definitions[:] = [
            definition for definition in definitions if definition["node"] != node
        ]
        if len(definitions) < initial_count:
            self.logger.info(f"Removed {definition_type}: << {node} >>")

    def log_conversation_state(self):
        state_types = [
            self.allows,
            self.locks,
            self.unlocks,
            self.expects,
            self.primes,
            self.listens,
            self.initiates,
        ]

        log_message = []

        if any(state_types):
            log_message.append("Conversation state:")
            for items in state_types:
                for item in items:
                    node = item["node"]
                    time_left = item.get("timeLeft")
                    item_type = item.get("type")
                    labels = item.get("labels", [])
                    if time_left is not None:
                        time_left_str = f"({time_left:.2f})"
                    else:
                        time_left_str = "Infinite"
                    log_message.append(
                        f"{item_type}: {labels}: << {node} >> ({time_left_str}): {item}"
                    )

            log_message[1:] = sorted(log_message[1:])
        else:
            log_message.append("No items in conversation state")

        self.logger.info("\n".join(log_message) + "\n")


""" Initialize the audio player at the module level so it can be used in the process_node function, which is super deep in the function chain, without having to pass it to every single function before just to use it at the final step. """
audio_player = AudioPlayer(AUDIO_MAPPINGS_FILE_PATH, logger=logger)
audio_finished_event = threading.Event()
audio_started_event = threading.Event()
first_callback_made = threading.Event()

node_thread = None


def get_node_data(
    session: Session,
    text: str,
    labels: list[str],
    conversation_state: ConversationState,
    source: QuerySource,
) -> Result | None:

    def process_any_matching_prompt_or_whisper():
        process_node(
            session, ANY_MATCHING_PROMPT_OR_WHISPER, conversation_state, source=SYSTEM
        )

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

    if result.peek() and source == USER and ("Prompt" in labels or "Whisper" in labels):
        process_any_matching_prompt_or_whisper()

    elif (
        not result.peek()
        and source == USER
        and ("Prompt" in labels or "Whisper" in labels)
    ):
        process_no_matching_prompt_or_whisper()
        return None

    return result


def define_labels_and_text(
    session: Session,
    text: str,
    conversation_state: ConversationState,
    source: QuerySource,
) -> list[str]:
    def meets_expectations():
        return any(
            text.lower() == item["node"].lower() for item in conversation_state.expects
        )

    def prompt_matches_allows():
        return any(
            text.lower() == item["node"].lower() for item in conversation_state.allows
        )

    def process_expectation_success():
        process_node(session, EXPECTATIONS_SUCCESS, conversation_state, source=SYSTEM)

    def process_expectation_failure():
        process_node(session, EXPECTATIONS_FAILURE, conversation_state, source=SYSTEM)

    labels = []
    if source == USER:

        if not conversation_state.expects:

            if prompt_matches_allows():
                labels.append("Prompt")

            if conversation_state.listens:
                labels.append("Whisper")

        elif meets_expectations():
            logger.info(f" << {text} >> meets conversation expectations")
            process_expectation_success()
            labels.append("Answer")
        else:
            logger.info(f" << {text} >> does not meet conversation expectations")
            process_expectation_failure()

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
            ]
        )

    return labels


def get_node_connections(
    session: Session,
    text: str,
    conversation_state: ConversationState,
    source: QuerySource,
) -> list[dict] | None:

    labels = define_labels_and_text(session, text, conversation_state, source)

    if not labels:
        labels = [
            "None"
        ]  # This will return no results from the database, but it will also not throw an error. We still want to call get_node_data (instead of making an early return) in order to call relevant nested functions inside.

    result = get_node_data(session, text, labels, conversation_state, source)

    if not result:
        return None

    result_data = [
        {
            "id": index,
            "start_node": dict(record["x"])["text"],  # x is the start node
            "relationship": record["r"].type,  # r is the relationship
            "end_node": dict(record["y"])["text"],  # y is the end node
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
    logger.debug(f"Waiting for first callback")
    first_callback_made.wait()
    logger.debug(f"First callback received, let's go")
    first_callback_made.clear()


def activate_connection_or_item(node_dict: dict, conversation_state: ConversationState):
    """Works for both activation connections (end_node) and dictionaries from the conversation state(node)."""
    node = node_dict.get("end_node") or node_dict.get("node")
    if not isinstance(node, str):
        logger.error(
            f"Failed to activate item: {node_dict}. Expected dict, got {type(node)}"
        )
        return

    print(node)
    node_labels = node_dict.get("labels", {}).get("end") or node_dict.get("labels")
    vocal_labels = ["Response", "Question", "Test"]

    if node_labels and any(node_label in vocal_labels for node_label in node_labels):
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
        activate_connection_or_item(connection, conversation_state)
        process_node(session, connection["end_node"], conversation_state, ROBEAU)


def process_and_logic_checks(connections: list[dict], attribute: list[dict]):
    return all(
        any(connection["end_node"] == item["node"] for item in attribute)
        for connection in connections
    )


def process_initial_logic_check(connection: dict, attribute: list[dict]):
    return any(connection["end_node"] == item["node"] for item in attribute)


def filter_logic_connections(connections: list[dict], logic_gate: str):
    initial_conditions_rel = {
        "IS_LOCKED",
        "IS_UNLOCKED",
        "IS_EXPECTED",
        "IS_PRIMED",
        "IS_LISTENED",
        "IS_INITIATED",
    }
    and_conditions_rel = {
        "AND_IS_LOCKED",
        "AND_IS_UNLOCKED",
        "AND_IS_EXPECTED",
        "AND_IS_PRIMED",
        "AND_IS_LISTENED",
        "AND_IS_INITIATED",
    }

    initial_conn = None
    and_conns = []
    then_conns = []
    other_conns = []

    for conn in connections:
        if conn["relationship"] in initial_conditions_rel:
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
        "IS_LOCKED": conversation_state.locks,
        "IS_UNLOCKED": conversation_state.unlocks,
        "IS_EXPECTED": conversation_state.expects,
        "IS_PRIMED": conversation_state.primes,
        "IS_LISTENED": conversation_state.listens,
        "IS_INITIATED": conversation_state.initiates,
    }
    for key, value in attribute_map.items():
        if key in relationship:
            return value
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
    conversation_state: ConversationState,
    method: str,
):
    method_map = {
        "delay_item": lambda end_node, params: conversation_state.delay_item(
            end_node, end_node_label, params.get("duration")
        ),  # unused, might change in the future
        "disable_item": lambda end_node, params: conversation_state.disable_item(
            end_node
        ),
        "apply_definitions": lambda end_node, params: conversation_state.apply_definitions(
            session, end_node
        ),
        "revert_definitions": lambda end_node, params: conversation_state.revert_definitions(
            session, end_node
        ),
    }

    if method in method_map:
        for connection in connections:
            end_node = connection.get("end_node", "")
            end_node_label: list[str] = connection.get("labels", {}).get("end", [])
            params = connection.get("params", {})
            method_map[method](end_node, params)


def process_modifications_relationships(
    session: Session,
    relationships_map: dict[str, list[dict]],
    conversation_state: ConversationState,
):
    relationship_methods = {
        "DELAYS": "delay_item",  # Unused right now but may be used in the future
        "DISABLES": "disable_item",
        "APPLIES": "apply_definitions",
        "REVERTS": "revert_definitions",
    }
    for relationship, method in relationship_methods.items():
        connections = relationships_map.get(relationship, [])
        if connections:
            process_modifications_connections(
                session, connections, conversation_state, method
            )


def process_definitions_connections(
    connections: list[dict], conversation_state: ConversationState, method: str
):
    for connection in connections:
        end_node = connection.get("end_node", "")
        duration = connection.get("params", {}).get("duration")
        end_node_label = connection.get("labels", {}).get("end", [])
        getattr(conversation_state, method)(end_node, end_node_label, duration)


def process_definitions_relationships(
    session: Session,
    relationships_map: dict[str, list[dict]],
    conversation_state: ConversationState,
):
    relationship_methods = {
        "ALLOWS": "add_allows",
        "LOCKS": "add_locks",
        "UNLOCKS": "add_unlocks",
        "EXPECTS": "add_expects",
        "LISTENS": "add_listens",
        "PRIMES": "add_primes",
        "INITIATES": "add_initiates",
    }

    for relationship, method in relationship_methods.items():
        connections = relationships_map.get(relationship, [])
        if connections:
            process_definitions_connections(connections, conversation_state, method)

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
        activate_connection_or_item(connection, conversation_state)
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
    if (any(node == item["node"] for item in conversation_state.unlocks)) or (
        any(node == item["node"] for item in conversation_state.primes)
    ):
        logger.info(
            f"Successful attempt at connection: {list(connection.values())[1:4]}"
        )
        return True
    else:
        logger.info(f"Failed attempt at connection: {list(connection.values())[1:4]}")
    return False


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
        if any(node == item["node"] for item in conversation_state.locks):
            logger.info(f"Connection is locked: {list(connection.values())[1:4]}")
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
        conversation_state.reset_attribute("primes")

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
                not in ("CHECKS", "ATTEMPTS", "TRIGGERS", "DEFAULTS", "CUTOFFS")
            ]
        )
        if not silent and all_connections:
            logger.info(
                f"Processing connections for node << {node} >> ({source.name}):\n{formatted_connections}\n"
            )
        elif all_connections:
            logger.info(
                f"Processing SILENT connections (activation relationships were not applied) for node << {node} >> ({source.name}):\n{formatted_silent_connections} "
            )
        elif not all_connections:
            logger.warning(f"No connections found to process in {connections}")

    # Activation connections
    checks: list[dict] = []
    attempts: list[dict] = []
    triggers: list[dict] = []
    defaults: list[dict] = []
    cutsoffs: list[dict] = []
    # Definition connections
    allows: list[dict] = []
    locks: list[dict] = []
    unlocks: list[dict] = []
    expects: list[dict] = []
    listens: list[dict] = []
    primes: list[dict] = []
    initiates: list[dict] = []
    # Modification connections
    disables: list[dict] = []
    delays: list[dict] = []  # Unused right now but may be in the future
    reverts: list[dict] = []
    applies: list[dict] = []
    # Logic connections
    ifs: list[dict] = []

    relationships_map = {
        # Activations
        "CHECKS": checks,
        "ATTEMPTS": attempts,
        "TRIGGERS": triggers,
        "DEFAULTS": defaults,
        "CUTSOFF": cutsoffs,
        # Definitions
        "ALLOWS": allows,
        "LOCKS": locks,
        "UNLOCKS": unlocks,
        "EXPECTS": expects,
        "LISTENS": listens,
        "PRIMES": primes,
        "INITIATES": initiates,
        # Modifications
        "DISABLES": disables,
        "DELAYS": delays,  # Unused right now but may be in the future
        "APPLIES": applies,
        "REVERTS": reverts,
        # Logics checks
        "IF": ifs,
    }

    for connection in connections:
        relationship = connection["relationship"]
        if relationship in relationships_map:
            relationships_map[relationship].append(connection)

    log_formatted_connections(relationships_map)
    conversation_state.log_conversation_state()

    if not silent:
        end_nodes_reached = process_activation_relationships(
            relationships_map, conversation_state, cutoff
        )
    else:
        end_nodes_reached = []

    process_definitions_relationships(session, relationships_map, conversation_state)
    process_modifications_relationships(session, relationships_map, conversation_state)
    process_logic_relationships(session, relationships_map, conversation_state)

    return end_nodes_reached


def handle_transmission_output(
    transmission_node: str, conversation_state: ConversationState
):
    if transmission_node == RESET_EXPECTATIONS:
        conversation_state.reset_attribute("expects")


def process_node(
    session: Session,
    node: str,
    conversation_state: ConversationState,
    source: QuerySource,
    silent: Optional[bool] = False,
    cutoff: Optional[bool] = False,
):

    logger.info(f"Processing node: << {node} >> ({source.name})")

    connections = get_node_connections(
        session=session,
        text=node,
        conversation_state=conversation_state,
        source=source,
    )

    if not connections:
        logger.info(
            f"No connections obtain for node: << {node} >> from source {source.name}\n"
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
        if response_node in transmissions_output_aliases:
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

    logger.info(f"End of process for node: << {node} >> from source {source.name}\n")


def run_update_conversation_state(
    conversation_state: ConversationState,
    session: Session,
    stop_event: threading.Event,
    pause_event: threading.Event,
):
    while not stop_event.is_set():
        if not pause_event.is_set():
            conversation_state.update_timed_items(session)
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
    return driver, session, conversation_state, stop_event, update_thread, pause_event


def cleanup(driver, session, stop_event, update_thread):
    if session:
        session.close()
    if driver:
        driver.close()
    stop_event.set()
    update_thread.join()


def main():
    driver, session, conversation_state, stop_event, update_thread, pause_event = (
        initialize()
    )
    prompt_session: PromptSession = PromptSession()

    global node_thread

    try:
        while True:
            with patch_stdout():
                user_query = prompt_session.prompt("Query: ").strip().lower()

                # Check if --silent is in the user query
                if "--silent" in user_query:
                    silent = True
                    user_query = user_query.replace(
                        "--silent", ""
                    ).strip()  # Remove --silent from the query
                else:
                    silent = False

                if user_query == "exit":
                    print("Exiting...")
                    return False

                elif user_query == "stfu":
                    audio_player.stop_audio()
                    if node_thread:
                        node_thread.join()

                elif node_thread and node_thread.is_alive():
                    print(
                        f"Query refused, processing node: interrupt with << stfu >> if needed"
                    )

                elif (
                    conversation_state.allows
                    or conversation_state.expects
                    or conversation_state.listens
                ) and user_query:
                    node_thread = Thread(
                        target=process_node,
                        args=(session, user_query, conversation_state, USER, silent),
                    )
                    node_thread.start()
                elif user_query:
                    node_thread = Thread(
                        target=process_node,
                        args=(
                            session,
                            user_query,
                            conversation_state,
                            GREETING,
                            silent,
                        ),
                    )
                    node_thread.start()

    except Exception as e:
        print(f"Error occurred: {e}")
        logger.exception(e)
    finally:
        cleanup(driver, session, stop_event, update_thread)


if __name__ == "__main__":
    main()

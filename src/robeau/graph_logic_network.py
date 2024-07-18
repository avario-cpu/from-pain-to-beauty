import enum
import random
import threading
import time
from collections import defaultdict
from enum import auto
from logging import DEBUG, INFO
from src.robeau.audio_player import AudioPlayer
from neo4j import GraphDatabase, Result, Session
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from src.utils import helpers

SCRIPT_NAME = helpers.construct_script_name(__file__)
logger = helpers.setup_logger(SCRIPT_NAME, level=INFO)
audio_player = AudioPlayer("src/robeau/audio_mappings.json")


class QuerySource(enum.Enum):
    USER = auto()
    ROBEAU = auto()
    SYSTEM = auto()


class Transmissions(enum.Enum):
    # IMPORTANT: These values must match the database text values
    EXPECTATIONS_SET_MSG = "EXPECTATIONS SET"
    EXPECTATIONS_SUCCESS_MSG = "EXPECTATIONS SUCCESS"
    EXPECTATIONS_FAILURE_MSG = "EXPECTATIONS FAILURE"
    EXPECTATIONS_RESET_MSG = "RESET EXPECTATIONS"


# Query source aliases
USER = QuerySource.USER
ROBEAU = QuerySource.ROBEAU
SYSTEM = QuerySource.SYSTEM

# Transmission aliases (Communication between the script and the database)
EXPECTATIONS_SET = Transmissions.EXPECTATIONS_SET_MSG.value
EXPECTATIONS_SUCCESS = Transmissions.EXPECTATIONS_SUCCESS_MSG.value
EXPECTATIONS_FAILURE = Transmissions.EXPECTATIONS_FAILURE_MSG.value
RESET_EXPECTATIONS = Transmissions.EXPECTATIONS_RESET_MSG.value


class ConversationState:
    def __init__(self):
        # definitions
        self.locks: list[dict] = []
        self.unlocks: list[dict] = []
        self.expectations: list[dict] = []
        self.primes: list[dict] = []
        self.listens: list[dict] = []
        # activations
        self.initiations: list[dict] = []

    def _add_item(
        self, node: str, duration: float | None, item_list: list, item_type: str
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
                logger.info(f"Refreshed the time duration of {existing_item}")
                return

        item_list.append(
            {
                "type": item_type,
                "node": node,
                "timeLeft": duration,
                "duration": duration,
                "start_time": start_time,
            }
        )

    def add_unlock(self, node: str, duration: float | None):
        self._add_item(node, duration, self.unlocks, "unlock")

    def add_lock(self, node: str, duration: float | None):
        self._add_item(node, duration, self.locks, "lock")

    def add_expectation(self, node: str, duration: float | None):
        self._add_item(node, duration, self.expectations, "expectation")

    def add_prime(self, node: str, duration: float | None):
        self._add_item(node, duration, self.primes, "prime")

    def add_listens(self, node: str, duration: float | None):
        self._add_item(node, duration, self.listens, "listen")

    def add_initiation(self, node: str, duration: float | None):
        self._add_item(node, duration, self.initiations, "initiation")

    def delay_item(self, node: str, duration: float | None):
        """Unused right now but may be used in the future, Logic wise just know that the difference between this and add_initiation is that this is for items that are already in the conversation state, which means a previously processed node wont be processed again if they are pointed to with a DELAY relationship"""
        for node_list in [self.locks, self.unlocks, self.expectations, self.primes]:
            for item in node_list:
                if item["node"] == node:
                    self._add_item(node, duration, node_list, item["type"])

    def disable_item(self, node: str):
        for node_list in [self.primes, self.initiations]:
            for item in node_list:
                if item["node"] == node:
                    node_list.remove(item)
                    logger.info(f"Item disabled: {item}")
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
            logger.debug(f"Updated time for item: {item}")

    def _remove_expired(self, items: list) -> list:
        valid_items = []

        for item in items:
            self._update_time_left(item)
            time_left = item.get("timeLeft")
            if time_left is None or time_left > 0:
                valid_items.append(item)
            else:
                logger.info(f"Item has expired: {item}")

        return valid_items

    def _check_initiations(self, session: Session):
        ongoing_initiations = []
        complete_initiations = []

        for initiation in self.initiations:
            self._update_time_left(initiation)
            time_left = initiation.get("timeLeft")

            if time_left is None:
                raise ValueError(
                    f"Initiation has invalid duration {time_left}: {initiation}"
                )

            if time_left > 0:
                ongoing_initiations.append(initiation)
            else:
                logger.info(f"Initiation complete: {initiation}")
                complete_initiations.append(initiation)

        self.initiations = ongoing_initiations

        for initiation in complete_initiations:
            activate_node(initiation)
            process_node(session, initiation["node"], self, source=ROBEAU)

    def update_timed_items(self, session: Session):
        items_to_update = ["locks", "unlocks", "expectations", "primes", "listens"]
        for item in items_to_update:
            setattr(self, item, self._remove_expired(getattr(self, item)))
        self._check_initiations(session)

    def reset_attribute(self, attribute: str):
        valid_attributes = [
            "locks",
            "unlocks",
            "primes",
            "expectations",
            "listens",
            "initiations",
        ]

        if attribute in valid_attributes:
            if getattr(self, attribute, None):
                setattr(self, attribute, [])
                logger.info(f'Reset attribute: "{attribute}"')
        else:
            logger.error(f'Invalid attribute: "{attribute}"')

    def revert_definitions(self, session, node: str):
        """Reverts the locks and unlock which the target node had instilled on other nodes"""
        definitions_to_revert = (
            get_node_connections(
                session=session, text=node, source=ROBEAU, conversation_state=self
            )
            or []
        )
        readable_definitions = [
            (i["start_node"], i["relationship"], i["end_node"])
            for i in definitions_to_revert
        ]
        logger.info(f"Obtained definitions to revert: {readable_definitions}")

        for connection in definitions_to_revert:
            end_node = connection.get("end_node", "")

            self._revert_individual_definition("lock", end_node, self.locks)
            self._revert_individual_definition("unlock", end_node, self.unlocks)

    def _revert_individual_definition(
        self, definition_type: str, node: str, definitions: list
    ):
        initial_count = len(definitions)
        definitions[:] = [
            definition for definition in definitions if definition["node"] != node
        ]
        if len(definitions) < initial_count:
            logger.info(f'Removed {definition_type} for: "{node}"')

    def log_conversation_state(self):
        state_types = {
            "Lock": self.locks,
            "Unlock": self.unlocks,
            "Expectation": self.expectations,
            "Prime": self.primes,
            "Listen": self.listens,
            "Initiation": self.initiations,
        }

        log_message = []

        if any(state_types.values()):
            log_message.append("\nConversation state:")
            for state_name, items in state_types.items():
                for item in items:
                    log_message.append(f"{state_name}: list{item}")
            log_message.append(" ")
        else:
            log_message.append("No items in conversation state")

        logger.info("\n".join(log_message))


def get_node_data(
    session: Session, text: str, labels: list[str], source: QuerySource
) -> Result | None:
    labels_query = "|".join(labels)
    query = f"""
    MATCH (x:{labels_query})-[R]->(y)
    WHERE toLower(x.text) = toLower($text)
    RETURN x, R, y
    """
    result = session.run(query, text=text)

    if not result.peek() and "Prompt" in labels and source == USER:
        logger.warning(f'Prompt "{text}" not found in database')
        print(f"Sorry, didn't understand that...")
        return None

    return result


def define_labels_and_text(
    session: Session,
    text: str,
    conversation_state: ConversationState,
    source: QuerySource,
) -> list[str] | None:
    def meets_expectations():
        return any(
            item["node"].lower() == text.lower()
            for item in conversation_state.expectations
        )

    def process_expectation_success():
        process_node(session, EXPECTATIONS_SUCCESS, conversation_state, source=SYSTEM)

    def process_expectation_failure():
        process_node(session, EXPECTATIONS_FAILURE, conversation_state, source=SYSTEM)

    if source == USER:
        if not conversation_state.expectations:
            labels = ["Prompt", "Request"]
            if conversation_state.listens:
                labels.append("Whisper")

        elif meets_expectations():
            logger.info(f'"{text}" meets conversation expectations')
            process_expectation_success()
            labels = ["Answer"]
        else:
            logger.info(f'"{text}" does not meet conversation expectations')
            process_expectation_failure()
            return None  # abort processing initial target node: if it doesn't match the expectations then finding it within the database is irrelevant anyways
    elif source == ROBEAU:
        labels = ["Response", "Question", "Action", "LogicGate"]
    elif source == SYSTEM:
        labels = ["Input"]

    return labels


def get_node_connections(
    session: Session,
    text: str,
    conversation_state: ConversationState,
    source: QuerySource,
) -> list[dict] | None:

    labels = define_labels_and_text(session, text, conversation_state, source)

    if not labels:
        return None

    result = get_node_data(session, text, labels, source)

    if not result:
        return None

    result_data = [
        {
            "id": index,
            "start_node": dict(record["x"])["text"],  # x is the start node
            "relationship": record["R"].type,  # R is the relationship
            "end_node": dict(record["y"])["text"],  # y is the end node
            "params": dict(record["R"]),
            "labels": {
                "start": list(record["x"].labels),
                "end": list(record["y"].labels),
            },
        }
        for index, record in enumerate(result)
    ]

    return result_data


def process_logic_activations(
    session: Session,
    connections: list[dict],
    logic_gate: str,
    conversation_state: ConversationState,
):
    if not connections:
        logger.error(f'No "THEN" connection found for LogicGate: "{logic_gate}"')
        return

    for connection in connections:
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
            logger.warning(f'Atypical connection for logicGate {logic_gate}: "{conn}"')

    logger.info(
        f"LogicGate {logic_gate} connections: \nInitial: {initial_conn} \nAnd: {and_conns} \nThen: {then_conns}"
    )
    return initial_conn, and_conns, then_conns


def determine_attribute(conversation_state: ConversationState, relationship: dict):
    attribute_map = {
        "IS_LOCKED": conversation_state.locks,
        "IS_UNLOCKED": conversation_state.unlocks,
        "IS_EXPECTED": conversation_state.expectations,
        "IS_PRIMED": conversation_state.primes,
        "IS_LISTENED": conversation_state.listens,
        "IS_INITIATED": conversation_state.initiations,
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
            logger.info(f'No connections found for LogicGate: "{logic_gate}"')
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
        "revert_definitions": lambda end_node, params: conversation_state.revert_definitions(
            session, end_node
        ),
        "delay_item": lambda end_node, params: conversation_state.delay_item(
            end_node, params.get("duration")
        ),  # unused, might change in the future
        "disable_item": lambda end_node, params: conversation_state.disable_item(
            end_node
        ),
    }

    if method in method_map:
        for connection in connections:
            end_node = connection.get("end_node", "")
            params = connection.get("params", {})
            method_map[method](end_node, params)


def process_modifications_relationships(
    session: Session,
    relationships_map: dict[str, list[dict]],
    conversation_state: ConversationState,
):
    relationship_methods = {
        "DISABLES": "disable_item",
        "DELAYS": "delay_item",  # Unused right now but may be used in the future
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
        getattr(conversation_state, method)(end_node, duration)


def process_definitions_relationships(
    session: Session,
    relationships_map: dict[str, list[dict]],
    conversation_state: ConversationState,
):
    relationship_methods = {
        "LOCKS": "add_lock",
        "UNLOCKS": "add_unlock",
        "EXPECTS": "add_expectation",
        "LISTENS": "add_listens",
        "PRIMES": "add_prime",
        "INITIATES": "add_initiation",
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


def activate_node(node_dict: dict):
    """Output. Works for both activation connections (end_node) and dictionaries from the conversation state(node)."""
    output = node_dict.get("end_node") or node_dict.get("node")
    print(output)
    logger.info(f'>>> OUTPUT: "{output}" ')
    audio_player.play_audio(output)
    return node_dict


def activate_connections(connections: list[dict]):
    for connection in connections:
        activate_node(connection)
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
        logger.info(f'Selected response for random pool Id {pool_id} is: "{end_node}"')
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


def process_random_connections(random_connection: list[dict]) -> list[dict]:
    random_pool_groups: list[list[dict]] = define_random_pools(random_connection)
    selected_connections: list[dict] = select_random_connections(random_pool_groups)
    activate_connections(selected_connections)
    return selected_connections


def execute_attempt(
    connection: dict,
    node: str,
    conversation_state: ConversationState,
):
    if (any(item["node"] == node for item in conversation_state.unlocks)) or (
        any(item["node"] == node for item in conversation_state.primes)
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
        if any(item["node"] == node for item in conversation_state.locks):
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

    activated_connections.extend(process_random_connections(random_connections))
    activated_connections.extend(activate_connections(regular_connections))

    if activated_connections:
        # Reset primes after any successful activation that is not a Warning
        conversation_state.reset_attribute("primes")

    return activated_connections


def process_activation_relationships(
    relationships_map: dict[str, list[dict]], conversation_state: ConversationState
) -> list[str]:
    """Walk down the activation relationships priority order and return the end nodes reached."""
    priority_order = ["CHECKS", "ATTEMPTS", "TRIGGERS", "DEFAULTS"]
    end_nodes_reached = []

    for key in priority_order:
        if relationships_map[key]:
            activated = process_activation_connections(
                relationships_map[key],
                conversation_state,
                connection_type=key,
            )
            if activated:
                end_nodes_reached.extend([item["end_node"] for item in activated])
                break  # Stop processing further as we've found the activated connections

    return end_nodes_reached


def process_relationships(
    session: Session, connections: list[dict], conversation_state: ConversationState
) -> list[str]:
    formatted_connections = "\n".join([str(connection) for connection in connections])

    logger.info(f"Processing connections:\n{formatted_connections}\n")
    # Activation connections
    checks: list[dict] = []
    attempts: list[dict] = []
    triggers: list[dict] = []
    defaults: list[dict] = []
    # Definition connections
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
    # Logic connections
    ifs: list[dict] = []

    relationships_map = {
        # Activations
        "CHECKS": checks,
        "ATTEMPTS": attempts,
        "TRIGGERS": triggers,
        "DEFAULTS": defaults,
        # Definitions
        "LOCKS": locks,
        "UNLOCKS": unlocks,
        "EXPECTS": expects,
        "LISTENS": listens,
        "PRIMES": primes,
        "INITIATES": initiates,
        # Modifications
        "DISABLES": disables,
        "DELAYS": delays,  # Unused right now but may be in the future
        "REVERTS": reverts,
        # Logics checks
        "IF": ifs,
    }

    for connection in connections:
        relationship = connection["relationship"]
        if relationship in relationships_map:
            relationships_map[relationship].append(connection)

    end_nodes_reached = process_activation_relationships(
        relationships_map, conversation_state
    )

    process_definitions_relationships(session, relationships_map, conversation_state)
    process_modifications_relationships(session, relationships_map, conversation_state)
    process_logic_relationships(session, relationships_map, conversation_state)

    return end_nodes_reached


def process_node(
    session: Session,
    node: str,
    conversation_state: ConversationState,
    source: QuerySource,
):

    logger.info(f'Processing node: "{node}" ({source.name})')
    conversation_state.log_conversation_state()

    connections = get_node_connections(
        session=session,
        text=node,
        conversation_state=conversation_state,
        source=source,
    )

    if not connections:
        logger.info(f'End of process for node: "{node}" from source {source.name}')
        return

    response_nodes_reached = process_relationships(
        session, connections, conversation_state
    )

    for response_node in response_nodes_reached:
        if response_node == RESET_EXPECTATIONS:
            # Reset expectations any time they are met or definitively failed to be met (possibility for multiple tries)
            conversation_state.reset_attribute("expectations")
            continue
        # Process further nodes that are activated by the current node
        process_node(session, response_node, conversation_state, ROBEAU)

    logger.info(f'End of process for node: "{node}" from source {source.name}')


def listen_for_queries(session, conversation_state):
    prompt_session: PromptSession = PromptSession()
    while True:
        user_query = prompt_session.prompt("Query: ").strip()
        if user_query == "exit":
            print("Exiting...")
            return False
        elif user_query:
            process_node(
                session=session,
                node=user_query,
                conversation_state=conversation_state,
                source=USER,
            )


def run_update_conversation_state(
    conversation_state: ConversationState, session, stop_event: threading.Event
):
    while not stop_event.is_set():
        conversation_state.update_timed_items(session)
        time.sleep(1)  # Adjust the sleep duration as needed


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
    conversation_state = ConversationState()
    stop_event = threading.Event()
    update_thread = threading.Thread(
        target=run_update_conversation_state,
        args=(conversation_state, session, stop_event),
    )
    update_thread.start()
    return driver, session, conversation_state, stop_event, update_thread


def cleanup(driver, session, stop_event, update_thread):
    if session:
        session.close()
    if driver:
        driver.close()
    stop_event.set()
    update_thread.join()


def main():
    driver, session, conversation_state, stop_event, update_thread = initialize()
    prompt_session: PromptSession = PromptSession()

    try:
        while True:
            user_input = prompt_session.prompt("start or exit: ").lower()
            if user_input == "exit":
                print("Exiting...")
                break
            elif user_input == "start":
                listen_for_queries(
                    session,
                    conversation_state,
                )
    except Exception as e:
        print(f"Error occurred: {e}")
        logger.exception(e)
    finally:
        cleanup(driver, session, stop_event, update_thread)


if __name__ == "__main__":
    main()

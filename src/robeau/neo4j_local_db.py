import enum
import random
import threading
import time
from collections import defaultdict
from enum import auto

from neo4j import GraphDatabase, Result, Session
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from src.utils import helpers

SCRIPT_NAME = helpers.construct_script_name(__file__)
logger = helpers.setup_logger(SCRIPT_NAME)


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


class RelationshipType(enum.Enum):
    CHECKS = auto()
    ATTEMPTS = auto()
    TRIGGERS = auto()
    DEFAULTS = auto()

    LOCKS = auto()
    UNLOCKS = auto()
    EXPECTS = auto()
    PRIMES = auto()


USER = QuerySource.USER
ROBEAU = QuerySource.ROBEAU
SYSTEM = QuerySource.SYSTEM

EXPECTATIONS_SET = Transmissions.EXPECTATIONS_SET_MSG.value
EXPECTATIONS_SUCCESS = Transmissions.EXPECTATIONS_SUCCESS_MSG.value
EXPECTATIONS_FAILURE = Transmissions.EXPECTATIONS_FAILURE_MSG.value
RESET_EXPECTATIONS = Transmissions.EXPECTATIONS_RESET_MSG.value


CHECKS = RelationshipType.CHECKS
ATTEMPTS = RelationshipType.ATTEMPTS
TRIGGERS = RelationshipType.TRIGGERS
DEFAULTS = RelationshipType.DEFAULTS

LOCKS = RelationshipType.LOCKS
UNLOCKS = RelationshipType.UNLOCKS
EXPECTS = RelationshipType.EXPECTS
PRIMES = RelationshipType.PRIMES


class ConversationState:
    def __init__(self):
        self.locks = []
        self.unlocks = []
        self.expectations = []
        self.primes = []
        self.initiations = []

    def _add_item(
        self, node: str, duration: float | None, item_list: list, item_type: str
    ):
        start_time = time.time()

        for existing_item in item_list:
            if existing_item["node"] != node:
                continue

            if duration is None:  # None means infinite duration here
                return

            # Refresh duration if the item already exists
            existing_item["duration"] = duration    
            existing_item["timeLeft"] = duration
            existing_item["start_time"] = start_time
            logger.info(
                f'Refreshed the time duration of {existing_item}'
            )
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

    def add_initiation(self, node: str, duration: float | None):
        self._add_item(node, duration, self.initiations, "initiation")
    
    def delay_item(self, node: str, duration: float | None):
        """Unused right now but may be used in the future, Logic wise just know that the difference between this and add_initiation is that this is for items that are already in the conversation state, which means a previously processed node wont be processed again if they are related with a DELAY relationship"""
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

    def _update_time_left(self, item):
        current_time = time.time()
        start_time = item["start_time"]
        duration = item["duration"]
        time_left = item["timeLeft"]

        if time_left is not None:
            elapsed_time = current_time - start_time
            remaining_time = max(0, duration - elapsed_time)
            item["timeLeft"] = remaining_time
            logger.info(f"updated: {item}")

    def _remove_expired(self, items: list):
        valid_items = []
        for item in items:
            self._update_time_left(item)
            if item["timeLeft"] is None or item["timeLeft"] > 0:
                valid_items.append(item)
            else:
                logger.info(f"Item has expired: {item}")
        return valid_items

    def _check_initiations(self, session: Session):
        ongoing_initiations = []
        complete_initiations = []
        for initiation in self.initiations:
            self._update_time_left(initiation)
            if initiation["timeLeft"] is None:
                raise ValueError(f"Initiation has duration {initiation["timeLeft"]}: {initiation}")
            elif initiation["timeLeft"] > 0:
                ongoing_initiations.append(initiation)
            else:
                logger.info(f"Initiation complete: {initiation}")
                complete_initiations.append(initiation)
        self.initiations = ongoing_initiations
        for initiation in complete_initiations:
            activate_node(initiation)
            process_node(
                session,
                initiation["node"],
                self,
                QuerySource.ROBEAU,
            )

    def update_timed_items(self, session: Session):
        self.locks = self._remove_expired(self.locks)
        self.unlocks = self._remove_expired(self.unlocks)
        self.expectations = self._remove_expired(self.expectations)
        self.primes = self._remove_expired(self.primes)
        self._check_initiations(session)

    def reset_attribute(self, attribute: str):
        attributes: dict = {
            "locks": [],
            "unlocks": [],
            "primes": [],
            "expectations": [],
        }

        if attribute in attributes and isinstance(getattr(self, attribute, None), list):
            if getattr(self, attribute):
                setattr(self, attribute, attributes[attribute])
                logger.info(f'Reset attribute: "{attribute}"')
        else:
            logger.error(f'Invalid attribute: "{attribute}"')



    def revert_definitions(self, session, node: str):
        definitions_to_revert = get_node_connections(session=session, text=node, source=ROBEAU, conversation_state=self) or []
        readable_definitions = [(i['start_node'], i['relationship'], i['end_node']) for i in definitions_to_revert]
        logger.info(f"Obtained definitions to revert: {readable_definitions}")
        for connection in definitions_to_revert:
            node = connection.get("end_node", "")

            initial_lock_count = len(self.locks)
            self.locks = [lock for lock in self.locks if lock["node"] != node]
            if len(self.locks) < initial_lock_count:
                logger.info(f'Removed lock for: "{node}"')

            initial_unlock_count = len(self.unlocks)
            self.unlocks = [unlock for unlock in self.unlocks if unlock["node"] != node]
            if len(self.unlocks) < initial_unlock_count:
                logger.info(f'Removed unlock for: "{node}"')


    def log_conversation_state(self):
        conditions = (
            self.locks,
            self.unlocks,
            self.expectations,
            self.primes,
            self.initiations,
        )
        if any(conditions):
            logger.info("Conversation state -------------------")
        else:
            logger.info("No items in conversation state")
        for item in self.locks if self.locks else []:
            logger.info(f"Lock: {item}")
        for item in self.unlocks if self.unlocks else []:
            logger.info(f"Unlock: {item}")
        for item in self.expectations if self.expectations else []:
            logger.info(f"Expectation: {item}")
        for item in self.primes if self.primes else []:
            logger.info(f"Prime: {item}")
        for item in self.initiations if self.initiations else []:
            logger.info(f"Initiation: {item}")
        if any(conditions):
            logger.info("--------------------------------------")


def get_node_data(
    neo4j_session: Session, text: str, label: str, source: QuerySource
) -> Result:
    query = f"""
    MATCH (x:{label})-[R]->(y)
    WHERE toLower(x.text) = toLower("{text}")
    RETURN x, R, y
    """
    result = neo4j_session.run(query)

    if not result.peek() and label == "Prompt" and source == USER:
        logger.warning(f'Prompt "{text}" not found in database')
        print(f"Sorry, didn't understand that...")

    return result


def get_node_connections(
    session: Session,
    text: str,
    source: QuerySource,
    conversation_state: ConversationState,
) -> list[dict] | None:


    if source == USER:
        if not conversation_state.expectations:
            label = "Prompt"
        elif any(
            item["node"].lower() == text.lower()
            for item in conversation_state.expectations
        ):
            logger.info(f' "{text}" meets conversation expectations')
            process_node(
                session, EXPECTATIONS_SUCCESS, conversation_state, source=SYSTEM
            )  # First, we callback process_node to handle the "expectation success" logic
            label = "Answer"  # Then, we progress in the conversation nodes with the Answer node...
        else:
            logger.info(f' "{text}" does not meet conversation expectations')
            text = EXPECTATIONS_FAILURE
            label = "Transmission"
    elif source == ROBEAU:
        label = "Response"
    elif source == SYSTEM:
        label = "Transmission"

    result = get_node_data(session, text, label, source)

    if not result.peek():
        logger.info(f'No connections found for node: "{text}"')
        return None

    result_data = []

    for index, record in enumerate(result):
        x = record["x"]
        R = record["R"]
        y = record["y"]

        start_node_labels = [label for label in x.labels]
        start_node_props = dict(x)

        relationship_type = R.type
        relationship_props = dict(R)

        end_node_labels = [label for label in y.labels]
        end_node_props = dict(y)

        connection = {
            "id": index,
            "start_node": start_node_props["text"],
            "relationship": relationship_type,
            "end_node": end_node_props["text"],
            "params": relationship_props,
            "labels": {"start": start_node_labels, "end": end_node_labels},
        }

        result_data.append(connection)
    return result_data


def process_modifications_connections(session: Session, connections: list[dict], conversation_state: ConversationState, method: str):
    method_map = {
        "revert_definitions": lambda end_node, params: conversation_state.revert_definitions(session, end_node),
        "delay_item": lambda end_node, params: conversation_state.delay_item(end_node, params.get("duration")),  # unused, might chance in the future
        "disable_item": lambda end_node, params: conversation_state.disable_item(end_node)
    }

    if method in method_map:
        for connection in connections:
            end_node = connection.get("end_node", "")
            params = connection.get("params", {})
            method_map[method](end_node, params)


def process_modifications_relationships(session: Session, relationships_map: dict[str, list[dict]], conversation_state: ConversationState):
    relationship_methods = {
        "DISABLES": "disable_item",
        "DELAYS": "delay_item",  # Unused right now but may be used in the future
        "REVERTS": "revert_definitions",
    }
    for relationship, method in relationship_methods.items():
        connections = relationships_map.get(relationship, [])
        if connections:
            process_modifications_connections(session, connections, conversation_state, method)

  
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
        "PRIMES": "add_prime",
        "EXPECTS": "add_expectation",
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
    """Output. Works for both activation connections (end_node) and initiations from the conversation state(node)."""
    output = node_dict.get("end_node") or node_dict.get("node")
    print(output)
    logger.info(f'>>> OUTPUT: "{output}" ')
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

    if any(weight is None for weight in weights):
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
        connection: dict = select_random_connection(pooled_group)
        logger.info(
            f'Selected response for random pool Id {connection["params"].get("randomPoolId")} is: "{connection["end_node"]}"'
        )
        selected_connections.append(connection)
    return selected_connections


def define_random_pools(connections: list[dict]) -> list[list[dict]]:

    grouped_data = defaultdict(list)
    for connection in connections:
        grouped_data[connection["params"].get("randomPoolId", 0)].append(connection)

    result = list(grouped_data.values())

    formatted_pools = "\n".join(
        [
            f"\ngroup{index}:\n" + "\n".join([str(conn) for conn in group])
            for index, group in enumerate(result)
        ]
    )
    if result:
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
    connection_type: RelationshipType,
) -> list[dict]:
    random_connections: list[dict] = []
    connections_list: list[dict] = []
    activated_connections: list[dict] = []

    for connection in connections:
        node = connection["end_node"]
        if any(item["node"] == node for item in conversation_state.locks):
            logger.info(f"Connection is locked: {list(connection.values())[1:4]}")
            continue

        if connection_type == ATTEMPTS and not execute_attempt(
            connection,
            node,
            conversation_state,
        ):
            continue

        elif connection.get("params", {}).get("randomWeight"):
            random_connections.append(connection)
        else:
            connections_list.append(connection)

    activated_connections.extend(process_random_connections(random_connections))
    activated_connections.extend(activate_connections(connections_list))

    if activated_connections:
        # reset primes after any successful activation that are not Warnings
        conversation_state.reset_attribute("primes")

    return activated_connections


def process_activation_relationships(
    relationships_map: dict[str, list[dict]],
    conversation_state: ConversationState,
) -> list[str]:
    """Walk down the activation relationships priority order and return the end nodes reached."""

    activated_checks: list[dict] | None = (
        process_activation_connections(
            relationships_map["CHECKS"], conversation_state, connection_type=CHECKS
        )
        if relationships_map["CHECKS"]
        else None
    )

    activated_attempts: list[dict] | None = (
        process_activation_connections(
            relationships_map["ATTEMPTS"], conversation_state, connection_type=ATTEMPTS
        )
        if relationships_map["ATTEMPTS"] and not activated_checks
        else None
    )

    activated_triggers: list[dict] | None = (
        process_activation_connections(
            relationships_map["TRIGGERS"], conversation_state, connection_type=TRIGGERS
        )
        if relationships_map["TRIGGERS"]
        and not activated_attempts
        and not activated_checks
        else None
    )

    activated_defaults: list[dict] | None = (
        process_activation_connections(
            relationships_map["DEFAULTS"], conversation_state, connection_type=DEFAULTS
        )
        if relationships_map["DEFAULTS"]
        and not activated_checks
        and not activated_attempts
        and not activated_triggers
        else None
    )

    end_nodes_reached: list[str] = (
        [check["end_node"] for check in activated_checks or []]
        + [attempt["end_node"] for attempt in activated_attempts or []]
        + [trigger["end_node"] for trigger in activated_triggers or []]
        + [default["end_node"] for default in activated_defaults or []]
    )

    return end_nodes_reached


def process_relationships(
    session: Session, connections: list[dict], conversation_state: ConversationState
) -> list[str]:
    formatted_connections = "\n".join([str(connection) for connection in connections])

    logger.info(f"Processing connections:\n{formatted_connections}")
    # Activation connections
    checks: list[dict] = []
    attempts: list[dict] = []
    triggers: list[dict] = []
    defaults: list[dict] = []
    # Definition connections
    locks: list[dict] = []
    unlocks: list[dict] = []
    expects: list[dict] = []
    primes: list[dict] = []
    initiates: list[dict] = []
    # Modification connections
    disables: list[dict] = []
    delays: list[dict] = [] # Unused right now but may be used in the future
    reverts: list[dict] = []

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
        "PRIMES": primes,
        "INITIATES": initiates,
        # Modifications
        "DISABLES": disables,
        "DELAYS": delays, # unused right now but may be used in the future
        "REVERTS": reverts,
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
        process_node(session, response_node, conversation_state, ROBEAU)

    logger.info(f'End of process for node: "{node}"')


def listen_for_queries(
    session, conversation_state, specific_prompt, query_duration, prompt_session
):
    start_time = time.time()
    print(f"Specific prompt '{specific_prompt}' detected. Listening for query...")
    while time.time() - start_time < query_duration:
        user_query = prompt_session.prompt("Query: ").strip()
        if user_query == "exit":
            print("Exiting...")
            return False
        elif user_query:
            process_node(
                session=session,
                node=user_query,
                conversation_state=conversation_state,
                source=QuerySource.USER,
            )
            start_time = time.time()
    print("ran out of time")
    return True


def establish_connection():
    start_time = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    session = driver.session()
    session.run("RETURN 1").consume()  # Warmup query
    connection_time = time.time() - start_time
    print(f"Connection established in {connection_time:.3f} seconds")
    print(driver.get_server_info())
    return driver, session


def run_update_conversation_state(
    conversation_state: ConversationState, session: Session, stop_event: threading.Event
):
    while not stop_event.is_set():
        conversation_state.update_timed_items(session)
        time.sleep(1)  # Adjust the sleep duration as needed


def main():

    driver, session = None, None
    try:
        driver, session = establish_connection()
        conversation_state = ConversationState()

        stop_event = threading.Event()
        update_thread = threading.Thread(
            target=run_update_conversation_state,
            args=(conversation_state, session, stop_event),
        )
        update_thread.start()

        specific_prompt = "start"
        query_duration = 10

        prompt_session = PromptSession()

        with patch_stdout():
            while True:
                user_input = prompt_session.prompt("start or exit: ").strip().lower()
                if user_input == "exit":
                    print("Exiting...")
                    break
                elif user_input == specific_prompt:
                    listen_for_queries(
                        session,
                        conversation_state,
                        specific_prompt,
                        query_duration,
                        prompt_session,
                    )
    except Exception as e:
        print(f"Error occurred: {e}")
        logger.exception(e)
        raise
    finally:
        if session:
            session.close()
        if driver:
            driver.close()
        stop_event.set()
        update_thread.join()


if __name__ == "__main__":
    main()

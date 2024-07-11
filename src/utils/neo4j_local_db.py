import random
from neo4j import GraphDatabase
from neo4j import Session
import time
from collections import defaultdict
from src.core import utils
import enum
from enum import auto
from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

SCRIPT_NAME = utils.construct_script_name(__file__)
logger = utils.setup_logger(SCRIPT_NAME)


class NodeType(enum.Enum):
    PROMPT = auto()
    RESPONSE = auto()


class RelationshipType(enum.Enum):
    LOCKS = auto()
    CHECKS = auto()
    ATTEMPTS = auto()
    TRIGGERS = auto()
    DEFAULTS = auto()
    UNLOCKS = auto()
    EXPECTS = auto()


# Aliases for readability
ATTEMPTS = RelationshipType.ATTEMPTS
CHECKS = RelationshipType.CHECKS
DEFAULTS = RelationshipType.DEFAULTS
LOCKS = RelationshipType.LOCKS
TRIGGERS = RelationshipType.TRIGGERS
UNLOCKS = RelationshipType.UNLOCKS
EXPECTS = RelationshipType.EXPECTS


class ConversationState:
    def __init__(self):
        self.unlocks = []
        self.locks = []
        self.questioning = False

    def add_lock(self, lock):
        if lock not in self.locks:
            self.locks.append(lock)
            logger.info(f"Locked the node: '{lock}'")

    def add_unlock(self, unlock: dict[str, str | float | None]):
        node = unlock.get("node")
        duration = unlock.get("timeLeft")
        start_time = time.time()

        for existing_unlock in self.unlocks:
            if existing_unlock["node"] != node:
                continue

            if duration is None:
                logger.info(
                    f"Refused to unlock the node: '{node}' because it is infinite and already tracked."
                )
                return

            # Refresh the time duration
            existing_unlock["timeLeft"] = duration
            existing_unlock["start_time"] = start_time
            logger.info(f"Refreshed the time duration for node: '{node}'")
            return

        self.unlocks.append(
            {"node": node, "timeLeft": duration, "start_time": start_time}
        )
        logger.info(f"Unlocked the node: '{node}'")

    def calculate_unlock_timings(self, node: str):
        for unlock in self.unlocks:
            if unlock["node"] != node:
                continue

            if unlock["timeLeft"] is None:
                return None  # Infinite duration

            elapsed_time = time.time() - unlock["start_time"]
            remaining_time = unlock["timeLeft"] - elapsed_time
            return max(0, remaining_time)  # Ensure non-negative remaining time

        return None

    def get_unlocks(self):
        """Returns the formatted and updated unlocks with the remaining time left for each node."""
        updated_unlocks = []
        for unlock in self.unlocks:
            updated_unlock = unlock.copy()
            remaining_time = self.calculate_unlock_timings(unlock["node"])
            updated_unlock["timeLeft"] = (
                f"{remaining_time:.2f}" if remaining_time is not None else "Infinite"
            )
            updated_unlock["start_time"] = time.strftime(
                "%H:%M:%S", time.localtime(unlock["start_time"])
            )
            updated_unlocks.append(updated_unlock)
        return "\n".join(str(unlock) for unlock in updated_unlocks)


def get_node_connections(
    neo4j_session: Session,
    text: str,
    node_type: NodeType,
) -> list[dict] | None:
    start_time = time.time()
    if node_type == NodeType.PROMPT:
        result = neo4j_session.run(
            """
            MATCH (x:Prompt)-[R]->(y)
            WHERE (x.text) = $prompt_text
            RETURN x, R, y
            """,
            prompt_text=text,
        )
    elif node_type == NodeType.RESPONSE:
        result = neo4j_session.run(
            """
            MATCH (x:Response)-[R]->(y)
            WHERE (x.text) = $response_text
            RETURN x, R, y
            """,
            response_text=text,
        )

    if result is None:
        return None

    result_data = []

    for index, record in enumerate(result):
        x = record["x"]
        R = record["R"]
        y = record["y"]

        prompt_labels = [label for label in x.labels if label != "Prompt"]
        prompt_props = dict(x)

        relationship_type = R.type
        relationship_props = dict(R)

        response_labels = [label for label in y.labels if label != "Response"]
        response_props = dict(y)

        connection = {
            "id": index,
            "prompt": prompt_props["text"],
            "relationship": relationship_type,
            "response": response_props.get("text", None),
            "params": relationship_props,
            "labels": {"prompt": prompt_labels, "response": response_labels},
        }

        result_data.append(connection)
    return result_data


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
        logger.debug(f"Random pools defined: {formatted_pools}")

    return result


def select_random_connection(connections: list[dict] | dict) -> dict:
    if isinstance(connections, dict):  # only one connection passed
        logger.debug(f"Only one connection passed: {connections}")
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
        logger.debug(
            f"Selected response for random pool Id {connection['params']['randomPoolId']} is: '{connection['response']}'"
        )
        selected_connections.append(connection)
    return selected_connections


def activate_connections(connections: list[dict]):
    """Output."""
    for connection in connections:
        output = list(connection.values())[3]
        print(output)
        logger.info(f"\n Output: '{output}'\n")
    return connections


def process_random_connections(random_connection: list[dict]) -> list[dict]:
    random_pool_groups: list[list[dict]] = define_random_pools(random_connection)
    selected_connections: list[dict] = select_random_connections(random_pool_groups)
    activate_connections(selected_connections)
    return selected_connections


def process_defaults():
    """TODO: Implement process_defaults function"""
    pass


def execute_attempt(
    node: str,
    connection: dict,
    conversation_state: ConversationState,
):
    remaining_time = conversation_state.calculate_unlock_timings(node)
    if remaining_time is None or remaining_time <= 0:
        logger.info(
            f"Skipping locked or timed out connection: {list(connection.values())[1:4]}"
        )
        return False
    else:
        return True


def process_expects(connection: dict, conversation_state: ConversationState):
    pass


def process_connections(
    connections: list[dict],
    conversation_state: ConversationState,
    connection_type: RelationshipType,
) -> list[dict]:
    random_connections: list[dict] = []
    connections_list: list[dict] = []
    activated_connections: list[dict] = []

    for connection in connections:
        node = connection["response"]
        if node in conversation_state.locks:
            logger.info(f"Skipping locked connection: {list(connection.values())[1:4]}")
            continue

        if connection_type == ATTEMPTS and not execute_attempt(
            node,
            connection,
            conversation_state,
        ):
            continue

        elif connection_type == EXPECTS:
            process_expects(connection, conversation_state)

        if connection.get("params", {}).get("randomWeight"):
            random_connections.append(connection)
        else:
            connections_list.append(connection)

    activated_connections.extend(activate_connections(connections_list))
    activated_connections.extend(process_random_connections(random_connections))

    return activated_connections


def process_unlocks(connections: list[dict], conversation_state: ConversationState):
    for connection in connections:
        unlocked_node = {
            "node": connection.get("response"),
            "timeLeft": connection.get("params", {}).get("limitedDuration"),
        }
        conversation_state.add_unlock(unlocked_node)


def process_relationships(
    connections: list[dict], conversation_state: ConversationState
) -> list[str]:
    formatted_connections = "\n".join([str(connection) for connection in connections])
    logger.info(
        f"Processing relationships:\n{formatted_connections}\n"
        f"with unlocked responses :\n{conversation_state.get_unlocks()}\n"
        f"and locked responses: {conversation_state.locks}"
    )

    locks: list[dict] = []
    checks: list[dict] = []
    expects: list[dict] = []
    attempts: list[dict] = []
    triggers: list[dict] = []
    defaults: list[dict] = []
    unlocks: list[dict] = []

    globals

    relationships_map = {
        "LOCKS": locks,
        "CHECKS": checks,
        "ATTEMPTS": attempts,
        "TRIGGERS": triggers,
        "DEFAULTS": defaults,
        "UNLOCKS": unlocks,
        "EXPECTS": expects,
    }

    for connection in connections:
        relationship = connection["relationship"]
        if relationship in relationships_map:
            relationships_map[relationship].append(connection)

    for lock in locks:
        conversation_state.add_lock(lock["response"])

    activated_checks: list[dict] | None = (
        process_connections(checks, conversation_state, connection_type=CHECKS)
        if checks
        else None
    )

    activated_attempts: list[dict] | None = (
        process_connections(attempts, conversation_state, connection_type=ATTEMPTS)
        if attempts and not activated_checks
        else None
    )

    activated_triggers: list[dict] | None = (
        process_connections(triggers, conversation_state, connection_type=TRIGGERS)
        if triggers and not activated_attempts and not activated_checks
        else None
    )

    activated_defaults: list[dict] | None = (
        process_defaults()
        if defaults
        and not activated_checks
        and not activated_attempts
        and not activated_triggers
        else None
    )  # TODO: Implement process_defaults function

    if unlocks:
        process_unlocks(unlocks, conversation_state)

    response_nodes_reached: list[str] = (
        [check["response"] for check in activated_checks or []]
        + [attempt["response"] for attempt in activated_attempts or []]
        + [trigger["response"] for trigger in activated_triggers or []]
        + [default["response"] for default in activated_defaults or []]
    )

    if expects:
        process_connections(expects, conversation_state, connection_type=EXPECTS)
        # TODO Implement process_expectations

    return response_nodes_reached


def process_node(
    session: Session,
    node_text: str,
    conversation_state: ConversationState,
    node_type: NodeType,
):
    logger.info(f"Processing node: '{node_text}'...")
    connections = get_node_connections(session, text=node_text, node_type=node_type)

    if not connections:
        return

    response_nodes_reached = process_relationships(connections, conversation_state)
    logger.info(f"Response nodes reached: {response_nodes_reached}")

    for node_text in response_nodes_reached:
        process_node(session, node_text, conversation_state, NodeType.RESPONSE)


def establish_connection():
    start_time = time.time()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    session = driver.session()
    session.run("RETURN 1").consume()  # Warmup query
    connection_time = time.time() - start_time
    print(f"Connection established in {connection_time:.3f} seconds")
    print(driver.get_server_info())
    return driver, session


def listen_for_queries(session, conversation_state, specific_prompt, query_duration):
    start_time = time.time()
    print(f"Specific prompt '{specific_prompt}' detected. Listening for query...")
    while time.time() - start_time < query_duration:
        user_query = input("Query: ").strip().lower()
        if user_query == "exit":
            print("Exiting...")
            return False
        elif user_query:
            logger.info(f"\n\nNew query: {user_query}")
            process_node(
                session=session,
                node_text=user_query,
                conversation_state=conversation_state,
                node_type=NodeType.PROMPT,
            )
            start_time = time.time()
            print(f"Waiting for new query within {query_duration} seconds...\n")
    print("ran out of time")
    return True


def main():

    driver, session = None, None
    try:
        driver, session = establish_connection()
        conversation_state = ConversationState()
        specific_prompt = "start"
        query_duration = (
            10  # Duration in seconds to wait for a query after specific prompt
        )

        while True:
            user_input = input("start or exit: ").strip().lower()
            if user_input == "exit":
                print("Exiting...")
                break
            elif user_input == specific_prompt:
                listen_for_queries(
                    session, conversation_state, specific_prompt, query_duration
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


if __name__ == "__main__":
    main()

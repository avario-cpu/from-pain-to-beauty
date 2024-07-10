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


class ConversationState:
    def __init__(self):
        self.unlocks = []
        self.locks = []

    def add_lock(self, lock):
        if lock not in self.locks:
            self.locks.append(lock)
            logger.info(f"Locked the node: '{lock}'")

    def add_unlock(self, unlock):
        if unlock not in self.unlocks:
            self.unlocks.append(unlock)
            logger.info(f"Unlocked the node: '{unlock}'")


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

        prompt_labels = list(x.labels)
        prompt_props = dict(x)

        relationship_type = R.type
        relationship_props = dict(R)

        response_labels = list(y.labels)
        response_props = dict(y)

        connection = {
            "id": index,
            "prompt": prompt_props["text"],
            "relationship": relationship_type,
            "response": response_props.get("text", "N/A"),
            "params": relationship_props,
            "audio": response_props.get("audioFile", "N/A"),
        }

        result_data.append(connection)
    return result_data


def define_random_pools(connections: list[dict]) -> list[list[dict]]:

    grouped_data = defaultdict(list)
    for connection in connections:
        grouped_data[connection["params"]["randomPoolId"]].append(connection)

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


def activate_random_connections(random_pool_groups: list[list[dict]]) -> list[dict]:
    activated_connections = []
    for pooled_group in random_pool_groups:
        connection: dict = select_random_connection(pooled_group)
        logger.debug(
            f"Selected response for random pool Id {connection['params']['randomPoolId']} is: '{connection['response']}'"
        )
        activated_connections.append(activate_connection(connection))
    return activated_connections


def activate_connection(connection: dict):
    print(list(connection.values())[3])
    return connection


def process_random_connections(random_connection: list[dict]) -> list[dict]:
    random_pool_groups: list[list[dict]] = define_random_pools(random_connection)
    activated_connections: list[dict] = activate_random_connections(random_pool_groups)
    return activated_connections


def process_defaults():
    """TODO: Implement process_defaults function"""
    pass


def process_connections(
    connections: list[dict], conversation_state: ConversationState, connection_type: str
) -> list[dict]:
    random_connections = []
    connections_list = []
    activated_connections = []

    for connection in connections:
        if connection["response"] in conversation_state.locks:
            logger.info(f"Skipping locked connection: {connection}")
            continue
        if (
            connection_type == "attempt"
            and connection["response"] not in conversation_state.unlocks
        ):
            continue
        if connection.get("params", {}).get("randomWeight"):
            random_connections.append(connection)
        else:
            connections_list.append(connection)

    for connection in connections_list:
        activated_connections.append(activate_connection(connection))

    activated_connections.extend(process_random_connections(random_connections))

    return activated_connections


def process_unlocks(connections: list[dict], conversation_state: ConversationState):
    for connection in connections:
        unlocked_node = connection["response"]
        conversation_state.add_unlock(unlocked_node)


def process_relationships(
    connections: list[dict], conversation_state: ConversationState
) -> list[str]:
    formatted_connections = "\n".join([str(connection) for connection in connections])
    logger.info(
        f"Processing relationships:\n{formatted_connections}\n"
        f"with unlocked responses : {conversation_state.unlocks}\n"
        f"and locked responses: {conversation_state.locks}"
    )

    locks = []
    checks = []
    attempts = []
    triggers = []
    defaults = []
    unlocks = []

    for i in range(len(connections)):
        relationship = connections[i]["relationship"]
        if relationship == "LOCKS":
            locks.append(connections[i])
        elif relationship == "CHECKS":
            checks.append(connections[i])
        elif relationship == "ATTEMPTS":
            attempts.append(connections[i])
        elif relationship == "TRIGGERS":
            triggers.append(connections[i])
        elif relationship == "DEFAULTS":
            defaults.append(connections[i])
        elif relationship == "UNLOCKS":
            unlocks.append(connections[i])

    for lock in locks:
        conversation_state.add_lock(lock["response"])

    activated_checks: list[dict] | None = (
        process_connections(checks, conversation_state, connection_type="checks")
        if checks
        else None
    )

    activated_attempts: list[dict] | None = (
        process_connections(attempts, conversation_state, connection_type="attempt")
        if attempts and not activated_checks
        else None
    )

    activated_triggers: list[dict] | None = (
        process_connections(triggers, conversation_state, connection_type="trigger")
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

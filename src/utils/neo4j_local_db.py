import random
from neo4j import GraphDatabase
from neo4j import Session
import time
from collections import defaultdict
from src.core import utils
import enum
from enum import auto

SCRIPT_NAME = utils.construct_script_name(__file__)
logger = utils.setup_logger(SCRIPT_NAME)


class NodeType(enum.Enum):
    PROMPT = auto()
    RESPONSE = auto()


class ConversationState:
    def __init__(self):
        self.current_unlocks = []
        self.last_unlocks = []

    def add_unlock(self, unlock):
        self.current_unlocks.append(unlock)
        logger.info(f"Unlocked the node: '{unlock}'")

    def update_unlocks(self):
        logger.info(
            f"setting last unlocks: {self.last_unlocks} to current unlocks: {self.current_unlocks}"
        )
        self.last_unlocks = self.current_unlocks
        self.current_unlocks = []


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
            "audio": response_props.get("audioFile", "N/A"),
            "params": relationship_props,
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
            f"Selected response for random pool Id << {connection['params']['randomPoolId']} >> is: {connection['response']}"
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


def process_defaults(defaults: list[dict]) -> dict:
    selected_default = select_random_connection(defaults)
    activate_connection(selected_default)
    return selected_default


def process_triggers(connections: list[dict]) -> list[dict]:
    random_triggers = []
    guaranteed_triggers = []
    activated_triggers = []

    for trigger in connections:
        if trigger["params"]["isRandom"]:
            random_triggers.append(trigger)
        else:
            guaranteed_triggers.append(trigger)

    activated_triggers.extend(process_random_connections(random_triggers))
    for trigger in guaranteed_triggers:
        activated_triggers.append(activate_connection(trigger))
    return activated_triggers


def process_attempts(
    connections: list[dict], conversation_state: ConversationState, defaults: list[dict]
) -> list[dict]:
    successful_attempts: list[dict] = []
    activated_connections: list[dict] = []

    for connection in connections:
        if connection["response"] in conversation_state.last_unlocks:
            successful_attempts.append(connection)

    for connection in successful_attempts:
        activated_connections.append(activate_connection(connection))

    if not successful_attempts:
        logger.info("No successful attempts found. Processing defaults...")
        activated_connections.append(process_defaults(defaults))

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
        f"with unlocked responses : {conversation_state.last_unlocks}"
    )

    triggers = []
    unlocks = []
    attempts = []
    defaults = []

    for i in range(len(connections)):
        relationship = connections[i]["relationship"]
        if relationship == "TRIGGERS":
            triggers.append(connections[i])
        elif relationship == "UNLOCKS":
            unlocks.append(connections[i])
        elif relationship == "ATTEMPTS":
            attempts.append(connections[i])
        elif relationship == "DEFAULTS":
            defaults.append(connections[i])

    activated_triggers: list[dict] | None = (
        process_triggers(triggers) if triggers else None
    )
    activated_attempts: list[dict] | None = (
        process_attempts(attempts, conversation_state, defaults) if attempts else None
    )
    if unlocks:
        process_unlocks(unlocks, conversation_state)

    response_nodes_reached: list[str] = [
        trigger["response"] for trigger in activated_triggers or []
    ] + [attempt["response"] for attempt in activated_attempts or []]

    return response_nodes_reached


def process_node(
    session: Session,
    node_text: str,
    conversation_state: ConversationState,
    node_type: NodeType,
):
    logger.info(f"Processing node: {node_text}")
    connections = get_node_connections(session, text=node_text, node_type=node_type)

    if not connections:
        logger.info(f"No connections found for node: {node_text}")
        return

    response_nodes_reached = process_relationships(connections, conversation_state)
    logger.info(f"Response nodes reached: {response_nodes_reached}")

    for node_text in response_nodes_reached:
        process_node(session, node_text, conversation_state, NodeType.RESPONSE)


def main():
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = "adw[@#$u392a"

    # Measure connection establishment time
    start_time = time.time()
    driver = GraphDatabase.driver(uri, auth=(username, password))
    conversation_state = ConversationState()

    # Reuse session
    session = driver.session()

    try:
        session.run("RETURN 1").consume()  # Warmup query
        connection_time = time.time() - start_time
        print(f"Connection established in {connection_time:.3f} seconds")

        while True:
            user_input = input("Query: ").strip().lower()
            if user_input == "exit":
                print("Exiting...")
                break
            else:
                process_node(
                    session=session,
                    node_text=user_input,
                    conversation_state=conversation_state,
                    node_type=NodeType.PROMPT,
                )
                conversation_state.update_unlocks()
                logger.info(f"Waiting for new prompt...\n")
    except Exception as e:
        print(f"Error occurred: {e}")
        logger.exception(e)
        raise
    finally:
        # Close the session and driver
        session.close()
        driver.close()


if __name__ == "__main__":
    main()

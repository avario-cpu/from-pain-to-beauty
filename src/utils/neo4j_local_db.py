import random
from neo4j import GraphDatabase
from neo4j import Session
import time
from collections import defaultdict
from src.core import utils

SCRIPT_NAME = utils.construct_script_name(__file__)
logger = utils.setup_logger(SCRIPT_NAME)


class ConversationState:
    def __init__(self):
        self.current_unlocks = []
        self.last_unlocks = []

    def add_unlock(self, unlock):
        self.current_unlocks.append(unlock)

    def update_unlocks(self):
        self.last_unlocks = self.current_unlocks
        self.current_unlocks = []


def get_node_connections(
    neo4j_session: Session,
    prompt_text: str | None,
    response_text: str | None,
) -> list[dict] | None:
    start_time = time.time()
    if type(prompt_text) == str and response_text is None:
        result = neo4j_session.run(
            """
            MATCH (x:Prompt)-[R]->(y)
            WHERE (x.text) = $prompt_text
            RETURN x, R, y
            """,
            prompt_text=prompt_text,
        )
    elif prompt_text is None and type(response_text) == str:
        result = neo4j_session.run(
            """
            MATCH (x:Response)-[R]->(y)
            WHERE (x.text) = $response_text
            RETURN x, R, y
            """,
            response_text=response_text,
        )
    else:
        raise ValueError(
            "Must provide only one of prompt_text or response_text, of type str"
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


def define_random_pools(
    triggers: list[dict], print_output: bool = False
) -> list[list[dict]]:
    grouped_data = defaultdict(list)

    random_pool_ids = [trigger["params"]["randomPoolId"] for trigger in triggers]

    tuples_list = zip(random_pool_ids, triggers)

    for id, trigger in tuples_list:
        grouped_data[id].append(trigger)

    # Convert the grouped data to a list of lists
    result = list(grouped_data.values())

    if print_output:
        for index, group in enumerate(result):
            print(f"\ngroup{index}:")
            print(group, end="\n")
    return result


def select_random_connection(connections: list[dict]) -> dict:
    weights = [connection["params"]["randomWeight"] for connection in connections]
    total_weight = sum(weights)
    chosen_weight = random.uniform(0, total_weight)
    current_weight = 0
    for connection, weight in zip(connections, weights):
        current_weight += weight
        if current_weight >= chosen_weight:
            return connection
    return connections[-1]


def activate_random_triggers(random_triggers_groups: list[list[dict]]) -> list[dict]:
    activated_triggers = []
    for trigger_group in random_triggers_groups:
        selected_trigger: dict = select_random_connection(trigger_group)
        print(
            f"Selected trigger's response for pool Id << {selected_trigger['params']['randomPoolId']} >> is: {selected_trigger['response']}"
        )
        activated_triggers.append(selected_trigger)
    return activated_triggers


def process_triggers(triggers: list[dict]) -> list[dict]:
    random_triggers = []
    guaranteed_triggers = []

    for trigger in triggers:
        if trigger["params"]["isRandom"]:
            random_triggers.append(trigger)
        else:
            guaranteed_triggers.append(trigger)

    random_triggers_groups = define_random_pools(random_triggers, print_output=True)
    activated_triggers: list[dict] = activate_random_triggers(random_triggers_groups)
    return activated_triggers


def process_unlocks(unlocks: list[dict], conversation_state: ConversationState):
    for unlock in unlocks:
        unlocked_node = unlock["response"]
        conversation_state.add_unlock(unlocked_node)
    print(f"Unlocked the nodes: {conversation_state.current_unlocks()}\n")


def activate_attempts(successful_attempts: list[dict]):
    for attempt in successful_attempts:
        print(f"Attempted response: {attempt['response']}")


def process_attempts(
    attempts: list[dict], conversation_state: ConversationState, defaults: list[dict]
) -> list[dict]:
    successful_attempts = []

    for attempt in attempts:
        if attempt["response"] in conversation_state.last_unlocks:
            successful_attempts.append(attempt)

    if successful_attempts:
        activate_attempts(successful_attempts)
        return successful_attempts
    else:
        print("No successful attempts found\n")
        activated_default = process_defaults(defaults)
        return [activated_default]  # must be a list for other functions to work


def activate_default(default: dict):
    print(f"Default response: {default['response']}")


def process_defaults(defaults: list[dict]) -> dict:
    selected_default = select_random_connection(defaults)
    activate_default(selected_default)
    return selected_default


def process_relationships(
    connections: list[dict], conversation_state: ConversationState
) -> list[str]:
    formatted_connections = "\n".join([str(connection) for connection in connections])
    logger.debug(f"Processing relationships:\n{formatted_connections}")

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

    activated_triggers = process_triggers(triggers)
    activated_attempts = process_attempts(attempts, conversation_state, defaults)
    process_unlocks(unlocks, conversation_state)

    response_nodes_reached = []
    for trigger in activated_triggers:
        response_nodes_reached.append(trigger["response"])
    for attempt in activated_attempts:
        response_nodes_reached.append(attempt["response"])

    return response_nodes_reached


def process_prompt(session: Session, str: str, conversation_state: ConversationState):
    connections = get_node_connections(session, prompt_text=str, response_text=None)

    if connections is None:
        print("No connections found for the given prompt")
        return

    response_nodes_reached = process_relationships(connections, conversation_state)

    further_connections = []
    for node in response_nodes_reached:
        connections = get_node_connections(
            session, prompt_text=None, response_text=node
        )
        if connections:
            further_connections.extend(connections)

    if not further_connections:
        print("No further connections found for the given response")
        return

    process_relationships(further_connections, conversation_state)
    conversation_state.update_unlocks()


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
            user_input = (
                input(
                    "Enter 'hello' (or different node text value) to run the query or 'exit' to quit: "
                )
                .strip()
                .lower()
            )
            if user_input == "exit":
                print("Exiting...")
                break
            else:
                process_prompt(
                    session=session,
                    str=user_input,
                    conversation_state=conversation_state,
                )
    finally:
        # Close the session and driver
        session.close()
        driver.close()


if __name__ == "__main__":
    main()

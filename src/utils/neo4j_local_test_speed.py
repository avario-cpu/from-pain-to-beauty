import random
from neo4j import GraphDatabase
from neo4j import Session
import time
from collections import defaultdict


def get_node_connections(neo4j_session, prompt_text):
    start_time = time.time()
    result = neo4j_session.run(
        """
        MATCH (p:Prompt)-[R]-(x)
        WHERE (p.text) = $prompt_text
        RETURN p, R, x
        """,
        prompt_text=prompt_text,
    )
    # Define the data structure to store the result
    result_data = []

    for index, record in enumerate(result):
        p = record["p"]
        R = record["R"]
        x = record["x"]

        prompt_labels = list(p.labels)
        prompt_props = dict(p)

        relationship_type = R.type
        relationship_props = dict(R)

        response_labels = list(x.labels)
        response_props = dict(x)

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


def group_by_id(triggers, print_output=False):
    grouped_data = defaultdict(list)

    random_pool_ids = [trigger["params"]["randomPoolId"] for trigger in triggers]

    tuples_list = zip(random_pool_ids, triggers)

    for id, value in tuples_list:
        grouped_data[id].append(value)

    # Convert the grouped data to a list of lists
    result = list(grouped_data.values())

    if print_output:
        for index, group in enumerate(result):
            print(f"\ngroup{index}:")
            print(group, end="\n")
    return result


def select_random_trigger(triggers_group):
    # Assume each trigger has a "weight" property in the params for simplicity
    weights = [trigger["params"]["randomWeight"] for trigger in triggers_group]
    total_weight = sum(weights)
    chosen_weight = random.uniform(0, total_weight)
    current_weight = 0
    for trigger, weight in zip(triggers_group, weights):
        current_weight += weight
        if current_weight >= chosen_weight:
            return trigger


def activate_random_triggers(random_triggers_groups):
    for group in random_triggers_groups:
        selected_trigger = select_random_trigger(group)
        print(
            f"Selected trigger's response for pool Id {selected_trigger['params']['randomPoolId']}  is: {selected_trigger['response']}"
        )


def process_unlocks():
    pass


def process_triggers(trigger_connections):
    random_triggers = []
    guaranteed_triggers = []

    for trigger in trigger_connections:
        if trigger["params"]["isRandom"]:
            random_triggers.append(trigger)
        else:
            guaranteed_triggers.append(trigger)

    random_triggers_groups = group_by_id(random_triggers, print_output=True)
    activate_random_triggers(random_triggers_groups)


def process_relationships(connections):
    trigger_connections = []
    unlock_connections = []
    for i in range(len(connections)):
        relationship = connections[i]["relationship"]
        if relationship == "TRIGGERS":
            trigger_connections.append(connections[i])
        elif relationship == "UNLOCKS":
            unlock_connections.append(connections[i])
    process_triggers(trigger_connections)
    process_unlocks()


def parse_string(session: Session, str: str):
    connections = get_node_connections(session, prompt_text=str)
    for i in range(len(connections)):
        print(connections[i], end="\n")
    process_relationships(connections)


def main():
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = "adw[@#$u392a"

    # Measure connection establishment time
    start_time = time.time()
    driver = GraphDatabase.driver(uri, auth=(username, password))

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
                parse_string(session=session, str=user_input)
    finally:
        # Close the session and driver
        session.close()
        driver.close()


if __name__ == "__main__":
    main()

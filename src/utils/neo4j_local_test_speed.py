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


def group_by_id(tuples_list):
    grouped_data = defaultdict(list)

    for id, value in tuples_list:
        grouped_data[id].append(value)

    # Convert the grouped data to a list of lists
    result = list(grouped_data.values())
    return result


def process_triggers(trigger_ids, connections):
    random_triggers = []
    guaranteed_triggers = []

    for id in trigger_ids:
        is_random = connections[id]["params"]["isRandom"]
        if is_random:
            random_pool_id = connections[id]["params"]["randomPoolId"]
            random_triggers.append((random_pool_id, connections[id]))

    random_triggers = group_by_id(random_triggers)
    for trigger_group in random_triggers:
        print("\n")
        print(trigger_group, end="\n")


def process_relationships(connections):
    trigger_connections = []
    for i in range(len(connections)):
        relationship = connections[i]["relationship"]
        if relationship == "TRIGGERS":
            id = connections[i]["id"]
            trigger_connections.append(id)
    process_triggers(trigger_connections, connections)


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

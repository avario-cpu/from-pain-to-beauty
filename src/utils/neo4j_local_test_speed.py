from neo4j import GraphDatabase
from neo4j import Session
import time

# Replace with your local Neo4j connection details
uri = "bolt://localhost:7687"
username = "neo4j"
password = "adw[@#$u392a"  # Replace with your actual password

# Measure connection establishment time
start_time = time.time()
driver = GraphDatabase.driver(uri, auth=(username, password))


# Reuse session
session = driver.session()


def get_node_data(neo4j_session, prompt_text):
    start_time = time.time()
    result = neo4j_session.run(
        """
        MATCH (p:Prompt)-[R]-(x)
        WHERE (p.text) = $prompt_text
        RETURN p, R, x
        """,
        prompt_text=prompt_text,
    )
    elapsed_time = time.time() - start_time

    # Define the data structure to store the result
    result_data = []
    connections_list = []

    for record in result:
        p = record["p"]
        R = record["R"]
        x = record["x"]

        prompt_labels = list(p.labels)
        prompt_props = dict(p)

        relationship_type = R.type
        relationship_props = dict(R)

        response_labels = list(x.labels)
        response_props = dict(x)

        connection_string = (
            f'"{prompt_props['text']}" '  # the node with this matching text value...
            f'{relationship_type} '  # TRIGGERS/UNLOCKS...
            f'"{response_props['text']}"'  # this other node, containing this text value...
            f' (params: {relationship_props})'  # according to those parameters.
        )

        connection = {
            "prompt": prompt_props["text"],
            "relationship": relationship_type,
            "response": response_props.get("text", "N/A"),
            "params": relationship_props
        }
        
        connections_list.append(connection_string)
        result_data.append(connection)

    for i in range(len(connections_list)):
        print(connections_list[i], end='\n')
    elapsed_time = time.time() - start_time
    print(f"Query + processing time: {elapsed_time:.3f} seconds")

    return result_data


def parse_string(session: Session, str: str):
    result = get_node_data(session, prompt_text=str)
    for i in range(len(result)):
        print(result[i], end='\n')


try:
    session.run("RETURN 1").consume()  # Warmup query
    connection_time = time.time() - start_time
    print(f'Connection established in {connection_time:.3f} seconds')

    while True:
        user_input = (
            input("Enter target node text value to run the query or 'exit' to quit: ").strip().lower()
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

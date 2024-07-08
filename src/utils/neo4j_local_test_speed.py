from neo4j import GraphDatabase
import time

# Replace with your local Neo4j connection details
uri = "bolt://localhost:7687"
username = "neo4j"
password = "adw[@#$u392a"  # Replace with your actual password

# Measure connection establishment time
start_time = time.time()
driver = GraphDatabase.driver(uri, auth=(username, password))
connection_time = time.time() - start_time
print(f"Connection established in {connection_time:.4f} seconds")

# Reuse session
session = driver.session()


def get_node_value(session, arg):
    start_time = time.time()
    result = session.run(
        """
        MATCH (p:Prompt)
        WHERE (p.text) = $prompt_text
        RETURN p.text AS value
        """,
        prompt_text=arg,
    )
    elapsed_time = time.time() - start_time
    for record in result:
        print(f"Node text: {record['value']}")
    print(f"Query executed in {elapsed_time:.4f} seconds")


# Warm-up query
session.run("RETURN 1").consume()

# Example usage
node_id = 0  # Replace with your node ID
get_node_value(session, arg="Hello!")

# Close the session and driver
session.close()
driver.close()

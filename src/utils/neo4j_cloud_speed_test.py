from neo4j import GraphDatabase
import time

# Replace with your Neo4j Aura connection details
uri = "neo4j+s://f6321f84.databases.neo4j.io"
username = "neo4j"
password = "j6wLX0Ux2zyvANQMXiNKIrK-VXkiV9irGYRmVnvqgIo"

driver = GraphDatabase.driver(uri, auth=(username, password))


def get_node_value(driver, node_id):
    with driver.session() as session:
        start_time = time.time()
        result = session.run(
            "MATCH (n) WHERE apoc.node.id(n) = $id RETURN n.text AS value", id=node_id
        )
        end_time = time.time()
        elapsed_time = end_time - start_time
        for record in result:
            print(f"Node text: {record['value']}")
        print(f"Query executed in {elapsed_time:.4f} seconds")


# Example usage
node_id = 1  # Replace with your node ID
get_node_value(driver, node_id)

driver.close()

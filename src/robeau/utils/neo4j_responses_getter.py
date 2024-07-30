import json
from neo4j import GraphDatabase

from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


class Neo4jToJson:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_filtered_nodes(self):
        with self.driver.session() as session:
            nodes = session.read_transaction(self._get_filtered_nodes)
        return nodes

    @staticmethod
    def _get_filtered_nodes(tx):
        query = """
        MATCH (n)
        WHERE ANY(label IN labels(n) WHERE label IN ['Response', 'Question', 'Test'])
        RETURN id(n) AS id, labels(n) AS labels, properties(n) AS properties
        """
        result = tx.run(query)
        nodes = []
        for record in result:
            node_data = {
                "id": record["id"],
                "labels": record["labels"],
                "properties": record["properties"],
                "audio_files": [{"file": "", "weight": 1}],
            }
            nodes.append(node_data)
        return nodes


def main():
    # Replace with your own connection details
    uri = NEO4J_URI
    user = NEO4J_USER
    password = NEO4J_PASSWORD

    neo4j_to_json = Neo4jToJson(uri, user, password)
    nodes = neo4j_to_json.get_filtered_nodes()
    neo4j_to_json.close()

    data = {"nodes": nodes}

    # Convert the data to JSON
    json_data = json.dumps(data, indent=4)
    print(json_data)

    # Save the JSON data to a file
    with open("src/robeau/jsons/raw_from_neo4j/neo4j_responses.json", "w") as f:
        f.write(json_data)


if __name__ == "__main__":
    main()

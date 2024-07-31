import json
from neo4j import GraphDatabase

from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


class Neo4jToJson:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_nodes_and_relationships(self):
        with self.driver.session() as session:
            nodes = session.read_transaction(self._get_all_nodes)
            relationships = session.read_transaction(self._get_all_relationships)
        return nodes, relationships

    @staticmethod
    def _get_all_nodes(tx):
        query = "MATCH (n) RETURN id(n) AS id, labels(n) AS labels, properties(n) AS properties"
        result = tx.run(query)
        nodes = []
        for record in result:
            nodes.append(
                {
                    "id": record["id"],
                    "labels": record["labels"],
                    "properties": record["properties"],
                }
            )
        return nodes

    @staticmethod
    def _get_all_relationships(tx):
        query = """
        MATCH ()-[r]->()
        RETURN id(r) AS id, type(r) AS type, properties(r) AS properties, id(startNode(r)) AS startNodeId, id(endNode(r)) AS endNodeId
        """
        result = tx.run(query)
        relationships = []
        for record in result:
            relationships.append(
                {
                    "id": record["id"],
                    "type": record["type"],
                    "properties": record["properties"],
                    "startNodeId": record["startNodeId"],
                    "endNodeId": record["endNodeId"],
                }
            )
        return relationships


def main():
    # Replace with your own connection details
    uri = NEO4J_URI
    user = NEO4J_USER
    password = NEO4J_PASSWORD

    neo4j_to_json = Neo4jToJson(uri, user, password)
    nodes, relationships = neo4j_to_json.get_nodes_and_relationships()
    neo4j_to_json.close()

    data = {"nodes": nodes, "relationships": relationships}

    # Convert the data to JSON
    json_data = json.dumps(data, indent=4)
    print(json_data)

    # Save the JSON data to a file
    with open("src/robeau/jsons/raw_from_neo4j/neo4j_all_data.json", "w") as f:
        f.write(json_data)


if __name__ == "__main__":
    main()

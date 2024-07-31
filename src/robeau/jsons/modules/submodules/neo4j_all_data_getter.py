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
        query = "MATCH (n) RETURN apoc.node.id(n) AS id, labels(n) AS labels, properties(n) AS properties"
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
        MATCH (startNode)-[r]->(endNode)
        RETURN 
            apoc.rel.id(r) AS id, 
            type(r) AS type, 
            properties(r) AS properties, 
            apoc.node.id(startNode) AS startNodeId, 
            apoc.node.id(endNode) AS endNodeId, 
            startNode.text AS startNodeText, 
            endNode.text AS endNodeText
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
                    "startNodeText": record.get("startNodeText"),
                    "endNodeText": record.get("endNodeText"),
                }
            )
        return relationships


def load_previous_state(file_path):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {"nodes": [], "relationships": []}


def compare_states(previous, current):
    changes: dict = {
        "added": {"nodes": [], "relationships": []},
        "removed": {"nodes": [], "relationships": []},
        "modified": {"nodes": [], "relationships": []},
    }

    previous_nodes = {node["id"]: node for node in previous["nodes"]}
    current_nodes = {node["id"]: node for node in current["nodes"]}

    previous_relationships = {rel["id"]: rel for rel in previous["relationships"]}
    current_relationships = {rel["id"]: rel for rel in current["relationships"]}

    # Compare nodes
    for node_id, node in current_nodes.items():
        if node_id not in previous_nodes:
            changes["added"]["nodes"].append(node)
        elif node != previous_nodes[node_id]:
            changes["modified"]["nodes"].append(
                {"before": previous_nodes[node_id], "after": node}
            )
    for node_id, node in previous_nodes.items():
        if node_id not in current_nodes:
            changes["removed"]["nodes"].append(node)

    # Compare relationships
    for rel_id, rel in current_relationships.items():
        if rel_id not in previous_relationships:
            changes["added"]["relationships"].append(rel)
        elif rel != previous_relationships[rel_id]:
            changes["modified"]["relationships"].append(
                {"before": previous_relationships[rel_id], "after": rel}
            )
    for rel_id, rel in previous_relationships.items():
        if rel_id not in current_relationships:
            changes["removed"]["relationships"].append(rel)

    return changes


def log_changes(changes, log_file_path):
    log_entries = []

    for node in changes["added"]["nodes"]:
        log_entries.append(f"Added node {node['id']}: {node}")

    for node in changes["removed"]["nodes"]:
        log_entries.append(f"Removed node {node['id']}: {node}")

    for change in changes["modified"]["nodes"]:
        log_entries.append(
            f"Modified node {change['before']['id']} from {change['before']} to {change['after']}"
        )

    for rel in changes["added"]["relationships"]:
        log_entries.append(f"Added relationship {rel['id']}: {rel}")

    for rel in changes["removed"]["relationships"]:
        log_entries.append(f"Removed relationship {rel['id']}: {rel}")

    for change in changes["modified"]["relationships"]:
        log_entries.append(
            f"Modified relationship {change['before']['id']} from {change['before']} to {change['after']}"
        )

    with open(log_file_path, "w") as log_file:
        log_file.write("\n".join(log_entries))


def main():
    uri = NEO4J_URI
    user = NEO4J_USER
    password = NEO4J_PASSWORD
    json_file_path = "src/robeau/jsons/raw_from_neo4j/neo4j_all_data.json"
    additions_file_path = (
        "src/robeau/jsons/temp/outputs_from_get_data/last_additions.json"
    )
    deletions_file_path = (
        "src/robeau/jsons/temp/outputs_from_get_data/last_deletions.json"
    )
    log_file_path = "src/robeau/jsons/temp/outputs_from_get_data/neo4j_changes_log.txt"
    backup_file_path = (
        "src/robeau/jsons/temp/outputs_from_get_data/OLD_neo4j_all_data.json"
    )

    neo4j_to_json = Neo4jToJson(uri, user, password)
    nodes, relationships = neo4j_to_json.get_nodes_and_relationships()
    neo4j_to_json.close()

    current_state = {"nodes": nodes, "relationships": relationships}
    previous_state = load_previous_state(json_file_path)

    changes = compare_states(previous_state, current_state)
    log_changes(changes, log_file_path)

    additions = {
        "nodes": changes["added"]["nodes"],
        "relationships": changes["added"]["relationships"],
    }
    deletions = {
        "nodes": changes["removed"]["nodes"],
        "relationships": changes["removed"]["relationships"],
    }

    json_data = json.dumps(current_state, indent=4)
    with open(json_file_path, "w") as f:
        f.write(json_data)

    write_json(additions_file_path, additions)
    write_json(deletions_file_path, deletions)
    write_json(backup_file_path, previous_state)

    print(f"Old file backed up as {backup_file_path}")
    print(f"Merged file saved to {json_file_path}")
    print(f"Additions saved to {additions_file_path}")
    print(f"Deletions saved to {deletions_file_path}")
    print(f"Log saved to {log_file_path}")


def write_json(file_path, data):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


if __name__ == "__main__":
    main()

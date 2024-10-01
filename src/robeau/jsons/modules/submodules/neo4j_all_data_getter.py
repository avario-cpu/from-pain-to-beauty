from dataclasses import dataclass
import json
import os
from typing import Any

from neo4j import GraphDatabase

from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, PROJECT_DIR_PATH


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
    def _get_all_nodes(tx) -> list[dict[str, Any]]:
        query = """MATCH (n) RETURN apoc.node.id(n) AS id, labels(n) AS labels,
        properties(n) AS properties"""
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
    def _get_all_relationships(tx) -> list[dict[str, Any]]:
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


def load_previous_state(file_path: str) -> dict[str, list[dict[str, Any]]]:
    """Load the previous state of the JSON this module is meant to output.

    Args: file_path: The path to the previous JSON file to load.

    Returns: The data from the JSON file. Should be a dictionary with two main keys:
        "nodes" and "relationships", each containing a list of dictionaries with their
        respective elements.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return data


def compare_states(
    previous: dict[str, list[dict[str, Any]]], current: dict[str, list[dict[str, Any]]]
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    changes = {
        "added": {"nodes": [], "relationships": []},
        "removed": {"nodes": [], "relationships": []},
        "modified": {"nodes": [], "relationships": []},
    }

    previous_nodes: dict[int, dict[str, Any]] = {
        node["id"]: node for node in previous["nodes"]
    }
    current_nodes: dict[int, dict[str, Any]] = {
        node["id"]: node for node in current["nodes"]
    }
    previous_relationships: dict[int, dict[str, Any]] = {
        rel["id"]: rel for rel in previous["relationships"]
    }
    current_relationships: dict[int, dict[str, Any]] = {
        rel["id"]: rel for rel in current["relationships"]
    }

    compare_items(previous_nodes, current_nodes, changes, "nodes")
    compare_items(
        previous_relationships, current_relationships, changes, "relationships"
    )

    return changes


def compare_items(
    previous_items: dict[int, dict],
    current_items: dict[int, dict],
    changes: dict[str, dict[str, list[dict]]],
    item_type: str,
):
    for item_id, item in current_items.items():
        if item_id not in previous_items:
            changes["added"][item_type].append(item)

        elif item != previous_items[item_id]:
            changes["modified"][item_type].append(
                {"before": previous_items[item_id], "after": item}
            )

    for item_id, item in previous_items.items():
        if item_id not in current_items:
            changes["removed"][item_type].append(item)


def log_changes(changes: dict[str, dict[str, list[dict]]], log_file_path: str):
    log_entries = []

    for node in changes["added"]["nodes"]:
        log_entries.append(f"Added node {node['id']}: {node}")

    for node in changes["removed"]["nodes"]:
        log_entries.append(f"Removed node {node['id']}: {node}")

    for change in changes["modified"]["nodes"]:
        log_entries.append(
            f"Modified node {change['before']['id']} from {change['before']}"
            " to {change['after']}"
        )

    for rel in changes["added"]["relationships"]:
        log_entries.append(f"Added relationship {rel['id']}: {rel}")

    for rel in changes["removed"]["relationships"]:
        log_entries.append(f"Removed relationship {rel['id']}: {rel}")

    for change in changes["modified"]["relationships"]:
        log_entries.append(
            f"Modified relationship {change['before']['id']} from {change['before']}"
            " to {change['after']}"
        )

    with open(log_file_path, "w") as log_file:
        log_file.write("\n".join(log_entries))


def create_file_paths_class():
    @dataclass
    class FilePaths:
        json: str
        additions: str
        deletions: str
        log: str
        backup: str

    return FilePaths(
        json=os.path.join(
            PROJECT_DIR_PATH, "src/robeau/jsons/neo4j/neo4j_all_data.json"
        ),
        additions=os.path.join(
            PROJECT_DIR_PATH,
            "src/robeau/jsons/temp/outputs_from_get_data/last_additions.json",
        ),
        deletions=os.path.join(
            PROJECT_DIR_PATH,
            "src/robeau/jsons/temp/outputs_from_get_data/last_deletions.json",
        ),
        log=os.path.join(
            PROJECT_DIR_PATH,
            "src/robeau/jsons/temp/outputs_from_get_data/neo4j_changes_log.txt",
        ),
        backup=os.path.join(
            PROJECT_DIR_PATH,
            "src/robeau/jsons/temp/outputs_from_get_data/OLD_neo4j_all_data.json",
        ),
    )


def main():
    file_paths = create_file_paths_class()

    neo4j_to_json = Neo4jToJson(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    nodes, relationships = neo4j_to_json.get_nodes_and_relationships()
    neo4j_to_json.close()

    current_state = {"nodes": nodes, "relationships": relationships}
    previous_state = load_previous_state(file_paths.json)

    changes = compare_states(previous_state, current_state)
    log_changes(changes, file_paths.log)

    additions = {
        "nodes": changes["added"]["nodes"],
        "relationships": changes["added"]["relationships"],
    }
    deletions = {
        "nodes": changes["removed"]["nodes"],
        "relationships": changes["removed"]["relationships"],
    }

    json_data = json.dumps(current_state, ident=2)
    with open(file_paths.json, "w") as f:
        f.write(json_data)

    write_json(file_paths.additions, additions)
    write_json(file_paths.deletions, deletions)
    write_json(file_paths.backup, previous_state)

    print(f"Old file backed up as {file_paths.backup}")
    print(f"Merged file saved to {file_paths.json}")
    print(f"Additions saved to {file_paths.additions}")
    print(f"Deletions saved to {file_paths.deletions}")
    print(f"Log saved to {file_paths.log}")


def write_json(file_path, data):
    with open(file_path, "w") as file:
        json.dump(data, file, ident=2)


if __name__ == "__main__":
    main()

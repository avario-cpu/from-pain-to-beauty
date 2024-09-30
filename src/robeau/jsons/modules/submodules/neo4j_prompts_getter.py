import json
import os
import string
from typing import Any

from neo4j import Driver, GraphDatabase, Record, Result, Session

from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, PROJECT_DIR_PATH
from src.robeau.core.robeau_constants import USER_LABELS


def clean_text(text: str) -> str:
    """
    Remove punctuation from text and convert to lowercase. This is necessary for making
    the prompt comparable to the text obtain from STT which is all lowercase and without
    punctuation.
    """
    allowed_punctuation = ["'", "-", "+", "*", "_"]
    translator = str.maketrans(
        "", "", "".join(c for c in string.punctuation if c not in allowed_punctuation)
    )
    cleaned_text = text.translate(translator)
    words = cleaned_text.split()
    cleaned_words = [word.lower() if word.lower() != "i" else "I" for word in words]
    return " ".join(cleaned_words)


def create_driver(uri: str, username: str, password: str) -> Driver:
    return GraphDatabase.driver(uri, auth=(username, password))


def run_query_for_label(session: Session, label: str) -> Result:
    query = """
    MATCH (n)
    WHERE $label IN labels(n)
    RETURN apoc.node.id(n) AS id, n
    """
    nodes = session.run(query, label=label)
    return nodes


def clean_node_data(node: Record) -> dict[str, Any]:
    """Remove punctuation from text and convert to lowercase using clean_text()."""
    node_data: dict[str, Any] = node["n"]
    cleaned_node_data = {"id": node["id"]}

    for key, value in node_data.items():
        if isinstance(value, str):
            cleaned_node_data[key] = clean_text(value)
        else:
            cleaned_node_data[key] = value

    return cleaned_node_data


def get_data_from_labels(labels: list[str]) -> dict[str, list[dict[str, Any]]]:
    driver = create_driver(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    with driver.session() as session:
        results: dict = {}

        for label in labels:
            nodes = run_query_for_label(session, label)

            for node in nodes:
                cleaned_node_data = clean_node_data(node)

                if label not in results:
                    results[label] = []
                results[label].append(cleaned_node_data)

        return results


def write_to_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def main():
    labels = USER_LABELS
    data = get_data_from_labels(labels)
    print("Data to be written to JSON:", data)
    json_filepath = os.path.join(
        PROJECT_DIR_PATH, "src/robeau/jsons/neo4j/neo4j_prompts.json"
    )

    if os.path.exists(json_filepath):
        write_to_json(data, json_filepath)
        print(f"Data has been written to {os.path.abspath(json_filepath)}")
    else:
        print(f"{json_filepath} was not found. Data was not written.")


if __name__ == "__main__":
    main()

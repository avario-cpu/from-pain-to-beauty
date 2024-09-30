import json
from neo4j import GraphDatabase
from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
import string
import os


def clean_text(text):
    allowed_punctuation = ["'", "-", "+", "*", "_"]
    translator = str.maketrans(
        "", "", "".join(c for c in string.punctuation if c not in allowed_punctuation)
    )
    cleaned_text = text.translate(translator)
    words = cleaned_text.split()
    cleaned_words = [word.lower() if word.lower() != "i" else "I" for word in words]
    return " ".join(cleaned_words)


def create_driver(uri, username, password):
    if uri:
        return GraphDatabase.driver(uri, auth=(username, password))
    return None


def run_query_for_label(session, label):
    query = f"MATCH (n:{label}) RETURN apoc.node.id(n) AS id, n"
    nodes = session.run(query)
    return nodes


def clean_node_data(node):
    node_data = node["n"]
    cleaned_node_data = {"id": node["id"]}
    for key, value in node_data.items():
        if isinstance(value, str):
            cleaned_node_data[key] = clean_text(value)
        else:
            cleaned_node_data[key] = value
    return cleaned_node_data


def get_data_from_labels(labels):
    uri = NEO4J_URI
    username = NEO4J_USER
    password = NEO4J_PASSWORD

    driver = create_driver(uri, username, password)

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
    labels = ["Greeting", "Prompt", "Answer", "Whisper", "Plea"]

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

from neo4j import GraphDatabase
import json
from src.config.settings import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
import string
import os

# Connect to Neo4j database
uri = NEO4J_URI
username = NEO4J_USER
password = NEO4J_PASSWORD

if uri:
    driver = GraphDatabase.driver(uri, auth=(username, password))


def clean_text(text):
    """Remove specific punctuation and handle capitalization."""
    allowed_punctuation = ["'", "-", "+", "*", "_"]  # keeping math symbols
    translator = str.maketrans(
        "", "", "".join(c for c in string.punctuation if c not in allowed_punctuation)
    )
    cleaned_text = text.translate(translator)

    words = cleaned_text.split()
    cleaned_words = [word.lower() if word.lower() != "i" else "I" for word in words]
    return " ".join(cleaned_words)


def get_text_keys_from_labels(labels):
    with driver.session() as session:
        results: dict = {}
        for label in labels:
            query = f"MATCH (n:{label}) RETURN n"
            nodes = session.run(query)
            for node in nodes:
                node_data = node["n"]
                for key, value in node_data.items():
                    if isinstance(value, str):
                        cleaned_value = clean_text(value)
                        if label not in results:
                            results[label] = []
                        results[label].append({key: cleaned_value})
        return results


def write_to_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


# List of labels to query
labels = ["Greeting", "Prompt", "Answer", "Whisper", "Plea"]

# Get text keys from specified labels
data = get_text_keys_from_labels(labels)

# Debug: Print the data to be written to the JSON file
print("Data to be written to JSON:", data)

# Write data to JSON file
json_filename = "C:\\Users\\ville\\MyMegaScript\\src\\robeau\\jsons\\db_strings.json"
write_to_json(data, json_filename)

# Check if the file exists and print the absolute path
if os.path.exists(json_filename):
    print(f"Data has been written to {os.path.abspath(json_filename)}")
else:
    print(f"Failed to write data to {json_filename}")

driver.close()

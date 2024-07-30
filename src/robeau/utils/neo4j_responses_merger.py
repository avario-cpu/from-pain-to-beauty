import json


def merge_json_files(
    old_file_path,
    new_file_path,
    merged_file_path,
    additions_file_path,
    deletions_file_path,
    log_file_path,
):
    with open(old_file_path, "r") as old_file, open(new_file_path, "r") as new_file:
        old_data = json.load(old_file)
        new_data = json.load(new_file)

    old_nodes = {node["id"]: node for node in old_data["nodes"]}
    new_nodes = {node["id"]: node for node in new_data["nodes"]}

    merged_nodes = []
    additions = []
    deletions = []
    log_entries = []

    for node_id, new_node in new_nodes.items():
        if node_id in old_nodes:
            old_node = old_nodes[node_id]
            # Check for property changes
            changes = []
            if new_node["properties"] != old_node["properties"]:
                changes.append(
                    f'Properties changed from {old_node["properties"]} to {new_node["properties"]}'
                )
            if set(new_node["labels"]) != set(old_node["labels"]):
                changes.append(
                    f'Labels changed from {old_node["labels"]} to {new_node["labels"]}'
                )

            if changes:
                log_entries.append(f"Node {node_id} updated: " + "; ".join(changes))

            # Preserve audio files and weight from the old node
            new_node["audio_files"] = old_node.get("audio_files", [])
            merged_nodes.append(new_node)
        else:
            # New node addition
            additions.append(new_node)
            merged_nodes.append(new_node)
            log_entries.append(f"Node {node_id} added: {new_node}")

    for node_id, old_node in old_nodes.items():
        if node_id not in new_nodes:
            # Node deletion
            deletions.append(old_node)
            log_entries.append(f"Node {node_id} deleted: {old_node}")

    merged_data = {"nodes": merged_nodes}
    additions_data = {"nodes": additions}
    deletions_data = {"nodes": deletions}

    with open(merged_file_path, "w") as merged_file:
        json.dump(merged_data, merged_file, indent=4)

    with open(additions_file_path, "w") as additions_file:
        json.dump(additions_data, additions_file, indent=4)

    with open(deletions_file_path, "w") as deletions_file:
        json.dump(deletions_data, deletions_file, indent=4)

    with open(log_file_path, "w") as log_file:
        log_file.write("\n".join(log_entries))


# Main file paths
old_file_path = "src/robeau/jsons/resp_merger_test/robeau_responses.json"
new_file_path = "src/robeau/jsons/resp_merger_test/robeau_responses.json"

# Result file paths
merged_file_path = "C:/Users/ville/MyMegaScript/src/robeau/jsons/resp_merger_test/merged_neo4j_data.json"
additions_file_path = "C:/Users/ville/MyMegaScript/src/robeau/jsons/resp_merger_test/additions_neo4j_data.json"
deletions_file_path = "C:/Users/ville/MyMegaScript/src/robeau/jsons/resp_merger_test/deletions_neo4j_data.json"
log_file_path = (
    "C:/Users/ville/MyMegaScript/src/robeau/jsons/resp_merger_test/merge_log.txt"
)

# Merge the files
merge_json_files(
    old_file_path,
    new_file_path,
    merged_file_path,
    additions_file_path,
    deletions_file_path,
    log_file_path,
)

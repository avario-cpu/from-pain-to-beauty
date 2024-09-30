import json


def load_json_data(old_file_path, new_file_path):
    with open(old_file_path, "r") as old_file, open(new_file_path, "r") as new_file:
        old_data = json.load(old_file)
        new_data = json.load(new_file)
    return old_data, new_data


def merge_nodes(old_nodes, new_nodes):
    merged_nodes = []
    additions = []
    deletions = []
    log_entries = []

    for node_id, new_node in new_nodes.items():
        if node_id in old_nodes:
            merged_node, changes = compare_and_merge_node(old_nodes[node_id], new_node)
            if changes:
                log_entries.append(f"Node {node_id} updated: " + "; ".join(changes))
            merged_nodes.append(merged_node)
        else:
            process_new_node(node_id, new_node, merged_nodes, additions, log_entries)

    for node_id, old_node in old_nodes.items():
        if node_id not in new_nodes:
            process_deleted_node(node_id, old_node, deletions, log_entries)

    return merged_nodes, additions, deletions, log_entries


def compare_and_merge_node(old_node, new_node):
    changes = []
    if new_node["properties"] != old_node["properties"]:
        changes.append(
            f'Properties changed from {old_node["properties"]} to {new_node["properties"]}'
        )
    if set(new_node["labels"]) != set(old_node["labels"]):
        changes.append(
            f'Labels changed from {old_node["labels"]} to {new_node["labels"]}'
        )

    new_node["audio_files"] = old_node.get("audio_files", [])

    return new_node, changes


def process_new_node(node_id, new_node, merged_nodes, additions, log_entries):
    merged_nodes.append(new_node)
    additions.append(new_node)
    log_entries.append(f"Node {node_id} added: {new_node}")


def process_deleted_node(node_id, old_node, deletions, log_entries):
    deletions.append(old_node)
    log_entries.append(f"Node {node_id} deleted: {old_node}")


def write_json_data(
    merged_data,
    additions_data,
    deletions_data,
    merged_file_path,
    additions_file_path,
    deletions_file_path,
):
    with open(merged_file_path, "w") as merged_file:
        json.dump(merged_data, merged_file, indent=2)

    with open(additions_file_path, "w") as additions_file:
        json.dump(additions_data, additions_file, indent=2)

    with open(deletions_file_path, "w") as deletions_file:
        json.dump(deletions_data, deletions_file, indent=2)


def write_log_entries(log_entries, log_file_path):
    with open(log_file_path, "w") as log_file:
        log_file.write("\n".join(log_entries))


def create_backup(old_data, backup_file_path):
    with open(backup_file_path, "w") as old_backup_file:
        json.dump(old_data, old_backup_file, indent=2)


def merge_json_files(
    old_file_path,
    new_file_path,
    additions_file_path,
    deletions_file_path,
    log_file_path,
    backup_file_path,
):
    old_data, new_data = load_json_data(old_file_path, new_file_path)

    old_nodes = {node["id"]: node for node in old_data["nodes"]}
    new_nodes = {node["id"]: node for node in new_data["nodes"]}

    merged_nodes, additions, deletions, log_entries = merge_nodes(old_nodes, new_nodes)

    merged_data = {"nodes": merged_nodes}
    additions_data = {"nodes": additions}
    deletions_data = {"nodes": deletions}

    write_json_data(
        merged_data,
        additions_data,
        deletions_data,
        old_file_path,
        additions_file_path,
        deletions_file_path,
    )
    write_log_entries(log_entries, log_file_path)
    create_backup(old_data, backup_file_path)

    print(f"Old file backed up as {backup_file_path}")
    print(f"Merged file saved to {old_file_path}")


def main():
    old_file_path = "src/robeau/jsons/processed_for_robeau/robeau_responses.json"
    new_file_path = "src/robeau/jsons/neo4j/neo4j_responses.json"
    additions_file_path = (
        "src/robeau/jsons/temp/outputs_from_responses_merge/last_additions.json"
    )
    deletions_file_path = (
        "src/robeau/jsons/temp/outputs_from_responses_merge/last_deletions.json"
    )
    log_file_path = (
        "src/robeau/jsons/temp/outputs_from_responses_merge/last_merge_log.txt"
    )
    backup_file_path = (
        "src/robeau/jsons/temp/outputs_from_responses_merge/OLD_robeau_responses.json"
    )

    merge_json_files(
        old_file_path,
        new_file_path,
        additions_file_path,
        deletions_file_path,
        log_file_path,
        backup_file_path,
    )


if __name__ == "__main__":
    main()

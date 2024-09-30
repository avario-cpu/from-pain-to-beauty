import json


def read_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def write_json(file_path, content):
    with open(file_path, "w") as file:
        json.dump(content, file, indent=2)


def merge_json_with_synonyms(old, new):
    protected_keys = ["StopCommand", "StopCommandRude", "StopCommandPolite"]
    protected_sub_keys = ["synonyms"]
    merged = {}
    additions = []
    deletions = []
    log_entries = []

    for key in new.keys():
        if key in old:
            original_nodes = {entry["id"]: entry for entry in old[key]}
            new_nodes = {entry["id"]: entry for entry in new[key]}
            merged[key], new_additions, new_log_entries = merge_entries(
                key, original_nodes, new_nodes, protected_sub_keys
            )
            additions.extend(new_additions)
            log_entries.extend(new_log_entries)
        else:
            merged[key], new_additions, new_log_entries = handle_additions(
                key, new[key]
            )
            additions.extend(new_additions)
            log_entries.extend(new_log_entries)

    for key in old.keys():
        if key not in new:
            if key in protected_keys:
                merged[key] = old[key]
                log_entries.append(f"Preserved key '{key}'")
            else:
                new_deletions, new_log_entries = handle_deletions(key, old[key])
                deletions.extend(new_deletions)
                log_entries.extend(new_log_entries)

    return merged, additions, deletions, log_entries


def merge_entries(key, original_nodes, new_nodes, protected_sub_keys):
    merged_list = []
    additions = []
    log_entries = []

    for node_id, new_entry in new_nodes.items():
        if node_id in original_nodes:
            merged_entry, changes = merge_single_entry(
                original_nodes[node_id], new_entry, protected_sub_keys
            )
            if changes:
                log_entries.append(
                    f"Updated entry for key '{key}', id '{node_id}': {', '.join(changes)}"
                )
            merged_list.append(merged_entry)
        else:
            merged_list.append(new_entry)
            additions.append(new_entry)
            log_entries.append(
                f"Added new entry for key '{key}', id '{node_id}': {new_entry}"
            )

    return merged_list, additions, log_entries


def merge_single_entry(original_entry, new_entry, protected_sub_keys):
    merged_entry = new_entry.copy()
    changes = []

    for sub_key in protected_sub_keys:
        if sub_key in original_entry and sub_key not in new_entry:
            merged_entry[sub_key] = original_entry[sub_key]

    for k, v in original_entry.items():
        if k == "id":
            continue
        if k not in new_entry and k not in protected_sub_keys:
            changes.append(f"{k} removed")
        elif k in new_entry and original_entry[k] != new_entry[k]:
            merged_entry[k] = new_entry[k]
            changes.append(f"{k} changed from {original_entry[k]} to {new_entry[k]}")

    return merged_entry, changes


def handle_additions(key, new_entries):
    merged_list = new_entries
    additions = new_entries
    log_entries = [f"Added all new entries for new key '{key}'"]

    return merged_list, additions, log_entries


def handle_deletions(key, old_entries):
    deletions = old_entries
    log_entries = [f"Key '{key}' removed"]

    return deletions, log_entries


def main():
    old_file_path = "src/robeau/jsons/processed_for_robeau/robeau_prompts.json"
    new_file_path = "src/robeau/jsons/neo4j/neo4j_prompts.json"
    log_file_path = (
        "src/robeau/jsons/temp/outputs_from_prompts_merge/last_merge_log.txt"
    )
    additions_file_path = (
        "src/robeau/jsons/temp/outputs_from_prompts_merge/last_additions.json"
    )
    deletions_file_path = (
        "src/robeau/jsons/temp/outputs_from_prompts_merge/last_deletions.json"
    )
    backup_file_path = (
        "src/robeau/jsons/temp/outputs_from_prompts_merge/OLD_robeau_prompts.json"
    )

    original_json = read_json(old_file_path)
    new_json = read_json(new_file_path)

    merged_json, additions, deletions, log_entries = merge_json_with_synonyms(
        original_json, new_json
    )

    write_json(backup_file_path, original_json)
    write_json(old_file_path, merged_json)
    write_json(additions_file_path, {"additions": additions})
    write_json(deletions_file_path, {"deletions": deletions})

    with open(log_file_path, "w") as log_file:
        log_file.write("\n".join(log_entries))

    print(f"Old file backed up as {backup_file_path}")
    print(f"Merged file saved to {old_file_path}")
    print(f"Additions saved to {additions_file_path}")
    print(f"Deletions saved to {deletions_file_path}")
    print(f"Log saved to {log_file_path}")


if __name__ == "__main__":
    main()

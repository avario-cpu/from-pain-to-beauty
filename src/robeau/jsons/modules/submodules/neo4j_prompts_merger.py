import json


def read_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def write_json(file_path, content):
    with open(file_path, "w") as file:
        json.dump(content, file, indent=4)


def merge_json_with_synonyms(old, new):
    preserved_keys = ["StopCommand", "StopCommandRude", "StopCommandPolite"]
    protected_subkeys = ["synonyms"]
    merged = {}
    additions = []
    deletions = []
    log_entries = []

    for key in new.keys():
        if key in old:
            original_nodes = {entry["id"]: entry for entry in old[key]}
            new_nodes = {entry["id"]: entry for entry in new[key]}

            merged_list = []

            for node_id, new_entry in new_nodes.items():
                if node_id in original_nodes:
                    original_entry = original_nodes[node_id]
                    merged_entry = new_entry.copy()

                    changes = []

                    for subkey in protected_subkeys:
                        if subkey in original_entry and subkey not in new_entry:
                            merged_entry[subkey] = original_entry[subkey]

                    for k, v in original_entry.items():
                        if k == "id":
                            continue
                        if k not in new_entry and k not in protected_subkeys:
                            changes.append(f"{k} removed")
                        elif k in new_entry and original_entry[k] != new_entry[k]:
                            merged_entry[k] = new_entry[k]
                            changes.append(
                                f"{k} changed from {original_entry[k]} to {new_entry[k]}"
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

            merged[key] = merged_list
        else:
            merged[key] = new[key]
            additions.extend(new[key])
            log_entries.append(f"Added all new entries for new key '{key}'")

    for key in old.keys():
        if key not in new:
            if key in preserved_keys:
                merged[key] = old[key]
                log_entries.append(f"Preserved key '{key}'")
            else:
                deletions.extend(old[key])
                log_entries.append(f"Key '{key}' removed")

    return merged, additions, deletions, log_entries


def main():
    old_file_path = "src/robeau/jsons/processed_for_robeau/robeau_prompts.json"
    new_file_path = "src/robeau/jsons/raw_from_neo4j/neo4j_prompts.json"
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
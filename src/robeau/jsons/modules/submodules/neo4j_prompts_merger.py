import json
import os
from typing import Any

from config.settings import PROJECT_DIR_PATH


def read_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def write_json(file_path, content):
    with open(file_path, "w") as file:
        json.dump(content, file, indent=2)


def merge_json_with_synonyms(
    robeau_prompts: dict[str, list[dict[str, Any]]],
    neo4j_prompts: dict[str, list[dict[str, Any]]],
):
    protected_keys = ["StopCommand", "StopCommandRude", "StopCommandPolite"]
    protected_sub_keys = ["synonyms"]
    merged = {}
    additions = []
    deletions = []
    log_entries = []

    for label in neo4j_prompts.keys():
        if label not in robeau_prompts:
            merged[label] = neo4j_prompts[label]
            additions.extend(neo4j_prompts[label])
            log_entries.append(
                f"Added all new prompts {neo4j_prompts[label]} for new label '{label}'"
            )

        elif label in robeau_prompts:
            original_prompts: dict[int, dict] = {
                prompt["id"]: prompt for prompt in robeau_prompts[label]
            }
            new_prompts: dict[int, dict] = {
                prompt["id"]: prompt for prompt in neo4j_prompts[label]
            }
            merged[label], new_additions, new_log_entries = merge_entries(
                label, original_prompts, new_prompts, protected_sub_keys
            )
            additions.extend(new_additions)
            log_entries.extend(new_log_entries)

    for label in robeau_prompts.keys():
        if label not in neo4j_prompts:
            if label in protected_keys:
                # do not delete protected keys such as StopCommand, they are only
                # present in the robeau json
                merged[label] = robeau_prompts[label]
                log_entries.append(f"Preserved key '{label}'")
            else:
                deletions.extend(robeau_prompts[label])
                log_entries.append(
                    f"Label '{label}' and all its members "
                    f"{robeau_prompts[label]} removed"
                )

    return merged, additions, deletions, log_entries


def merge_entries(
    label: str,
    original_prompts: dict[int, dict[str, Any]],
    new_prompts: dict[int, dict[str, Any]],
    protected_sub_keys: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    merged_result: list[dict[str, Any]] = []
    additions: list[dict[str, Any]] = []
    log_entries: list[str] = []

    for prompt_id, new_prompt in new_prompts.items():
        if prompt_id not in original_prompts:
            merged_result.append(new_prompt)
            additions.append(new_prompt)
            log_entries.append(f"Added new prompt for label '{label}': {new_prompt}")

        elif prompt_id in original_prompts:
            merged_entry, changes = merge_single_entry(
                original_prompts[prompt_id], new_prompt, protected_sub_keys
            )
            if changes:
                log_entries.append(
                    f"Updated prompt for label {label}: {', '.join(changes)}"
                )
            merged_result.append(merged_entry)

    return merged_result, additions, log_entries


def merge_single_entry(
    original_prompt: dict[str, Any],
    new_prompt: dict[str, Any],
    protected_sub_keys: list[str],
) -> tuple[dict[str, Any], list[str]]:
    """
    Merges a single prompt entry from the original and new prompt dictionaries.

    Args:
        original_prompt (dict): The original prompt entry.
        new_prompt (dict): The new prompt entry.
        protected_sub_keys (list): A list of sub-keys that should not be overwritten.

    Returns:
        A tuple containing the merged prompt and an informative list of changes made.
    """
    merged_prompt = new_prompt.copy()
    changes: list[str] = []

    for sub_key in protected_sub_keys:
        if sub_key in original_prompt and sub_key not in new_prompt:
            merged_prompt[sub_key] = original_prompt[sub_key]

    for k, _ in original_prompt.items():
        if k == "id":
            continue
        if k not in new_prompt and k not in protected_sub_keys:
            changes.append(f"{k} removed")
        elif k in new_prompt and original_prompt[k] != new_prompt[k]:
            merged_prompt[k] = new_prompt[k]
            changes.append(f"{k} changed from {original_prompt[k]} to {new_prompt[k]}")

    return merged_prompt, changes


def main():
    old_file_path = os.path.join(
        PROJECT_DIR_PATH, "src/robeau/jsons/robeau/robeau_prompts.json"
    )
    new_file_path = os.path.join(
        PROJECT_DIR_PATH, "src/robeau/jsons/neo4j/neo4j_prompts.json"
    )
    log_file_path = os.path.join(
        PROJECT_DIR_PATH,
        "src/robeau/jsons/temp/outputs_from_prompts_merge/last_merge_log.txt",
    )
    additions_file_path = os.path.join(
        PROJECT_DIR_PATH,
        "src/robeau/jsons/temp/outputs_from_prompts_merge/last_additions.json",
    )
    deletions_file_path = os.path.join(
        PROJECT_DIR_PATH,
        "src/robeau/jsons/temp/outputs_from_prompts_merge/last_deletions.json",
    )
    backup_file_path = os.path.join(
        PROJECT_DIR_PATH,
        "src/robeau/jsons/temp/outputs_from_prompts_merge/OLD_robeau_prompts.json",
    )

    robeau_prompts = read_json(old_file_path)  # the existing robeau prompts file
    neo4j_prompts = read_json(new_file_path)  # the new prompts file coming from neo4j

    merged_json, additions, deletions, log_entries = merge_json_with_synonyms(
        robeau_prompts, neo4j_prompts
    )

    write_json(backup_file_path, robeau_prompts)
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

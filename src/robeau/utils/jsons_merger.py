import json


# Function to read JSON content from a file
def read_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


# Function to write JSON content to a file
def write_json(file_path, content):
    with open(file_path, "w") as file:
        json.dump(content, file, indent=4)


# Function to merge the two JSON files
def merge_json_with_synonyms(original, new):
    merged = {}

    for key in new.keys():  # Iterate through keys in new_json, as it is the lead
        if key in original:
            # Create a dictionary for easy lookup of texts in original
            original_texts = {
                entry["text"]: entry for entry in original[key] if "text" in entry
            }
            # Create a dictionary for easy lookup of texts in new
            new_texts = {entry["text"]: entry for entry in new[key] if "text" in entry}

            # Create the merged list for the current key
            merged_list = []

            # Add or update entries based on new_texts
            for text, new_entry in new_texts.items():
                if text in original_texts:
                    # If the text exists in original, keep the original entry (with synonyms)
                    merged_list.append(original_texts[text])
                else:
                    # If the text is new, add it as is
                    merged_list.append(new_entry)

            # Add the merged list to the merged dictionary
            merged[key] = merged_list
        else:
            # If the key is only in new_json, add all its entries
            merged[key] = new[key]

    return merged


# File paths
original_file_path = "C:\\Users\\ville\\MyMegaScript\\src\\robeau\\jsons\\strings_with_synonyms.json"  # Path to the original JSON with synonyms
new_file_path = "C:\\Users\\ville\\MyMegaScript\\src\\robeau\\jsons\\db_strings.json"  # Path to the new JSON without synonyms
merged_file_path = "C:\\Users\\ville\\MyMegaScript\\src\\robeau\\jsons\\strings_with_synonyms_new.json"  # Path to save the merged JSON

# Read JSON content from files
original_json = read_json(original_file_path)
new_json = read_json(new_file_path)

# Merging the JSON files
merged_json = merge_json_with_synonyms(original_json, new_json)

# Write the merged JSON to a file
write_json(merged_file_path, merged_json)

# Print a confirmation message
print(f"Merged JSON has been saved to {merged_file_path}")

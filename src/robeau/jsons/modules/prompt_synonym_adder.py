import asyncio
import json
import threading
from logging import Logger
from typing import Optional

from src.core.constants import SUBPROCESSES_PORTS
from src.robeau.core.robeau_constants import (
    ROBEAU_PROMPTS_JSON_FILE_PATH as ROBEAU_PROMPTS,
)
from src.robeau.core.speech_recognition import recognize_speech

PORT = SUBPROCESSES_PORTS["synonym_adder"]


class SynonymHandler:
    def __init__(
        self,
        json_file_path: str,
        predefined_text: str,
        script_logger: Optional[Logger] = None,
    ):
        self.json_file_path = json_file_path
        self.predefined_text = predefined_text
        self.data = self.read_json()
        self.pause_event = threading.Event()  # Initialize pause event
        self.logger = script_logger

    def read_json(self):
        with open(self.json_file_path, "r") as f:
            return json.load(f)

    def write_json(self):
        with open(self.json_file_path, "w") as f:
            json.dump(self.data, f, indent=2)

    async def handle_message(self, message: str):
        synonym = message.strip().lower()
        response = input(
            f"Add synonym '{synonym}' for '{self.predefined_text}'? (y/n): "
        )
        if response.lower() == "y":
            self.add_synonym(self.predefined_text, synonym)
            self.write_json()
            print("Synonym added.")
        else:
            print("Synonym not added.")

    def add_synonym(self, text: str, synonym: str):
        for category in self.data:
            for entry in self.data[category]:
                if entry["text"] != text:
                    continue
                if "synonyms" not in entry:
                    entry["synonyms"] = []
                if synonym not in entry["synonyms"]:
                    entry["synonyms"].append(synonym)

                else:
                    print(f"Synonym {synonym} for {text} already exists.")
                return

        raise ValueError(f"Text '{text}' not found in any category.")


async def main():
    # Path to your JSON file
    json_file_path = ROBEAU_PROMPTS
    predefined_text = "nothing"  # Replace with the actual predefined text
    handler = SynonymHandler(
        json_file_path=json_file_path, predefined_text=predefined_text
    )

    await recognize_speech(handler)


if __name__ == "__main__":
    asyncio.run(main())

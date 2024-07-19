from src.connection.socket_server import BaseHandler
from typing import Optional
from logging import Logger
import json
import asyncio
from src.core.constants import SUBPROCESSES_PORTS
from src.robeau.core.robeau import launch_google_stt

PORT = SUBPROCESSES_PORTS["synonym_adder"]


class SynonymHandler(BaseHandler):
    def __init__(
        self,
        port: int,
        json_file_path: str,
        predefined_text: str,
        script_logger: Optional[Logger] = None,
    ):
        super().__init__(port, script_logger)
        self.json_file_path = json_file_path
        self.predefined_text = predefined_text
        self.data = self.read_json()

    def read_json(self):
        with open(self.json_file_path, "r") as f:
            return json.load(f)

    def write_json(self):
        with open(self.json_file_path, "w") as f:
            json.dump(self.data, f, indent=4)

    async def handle_message(self, message: str):
        synonym = message.strip().lower()
        response = input(
            f"Add synonym '{synonym}' for '{self.predefined_text}'? (y/n): "
        )
        if response.lower() == "y":
            self.add_synonym(self.predefined_text, synonym)
            self.write_json()
            self.writer.write(b"Synonym added.\n")
        else:
            self.writer.write(b"Synonym not added.\n")
        await self.writer.drain()

    def add_synonym(self, text: str, synonym: str):
        for category in self.data:
            for entry in self.data[category]:
                if entry["text"] == text:
                    if "synonyms" not in entry:
                        entry["synonyms"] = []
                    if synonym not in entry["synonyms"]:
                        entry["synonyms"].append(synonym)
                    else:
                        print(f"Synonym {synonym} for {text} already exists.")
                    return
        # If the text is not found, add a new entry
        self.data["NewCategory"] = self.data.get("NewCategory", []) + [
            {"text": text, "synonyms": [synonym]}
        ]


if __name__ == "__main__":
    # Path to your JSON file
    json_file_path = (
        "C:\\Users\\ville\\MyMegaScript\\src\\robeau\\jsons\\strings_with_syns.json"
    )
    predefined_text = "hello"  # Replace with the actual predefined text

    # Initialize and run the socket server with the SynonymHandler
    handler = SynonymHandler(
        port=PORT, json_file_path=json_file_path, predefined_text=predefined_text
    )

    launch_google_stt(interim=False, socket="synonym_adder")
    asyncio.run(handler.run_socket_server())

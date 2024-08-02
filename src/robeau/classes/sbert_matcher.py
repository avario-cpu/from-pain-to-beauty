import json
import time
from typing import Optional

import torch
from sentence_transformers import SentenceTransformer, util

from src.robeau.core.robeau_constants import (
    ROBEAU_PROMPTS_JSON_FILE_PATH as ROBEAU_PROMPTS,
)


class SBERTMatcher:
    def __init__(
        self,
        model_name="all-MiniLM-L6-v2",
        file_path=None,
        similarity_threshold=0.6,
    ):
        self.model = SentenceTransformer(model_name)
        if torch.cuda.is_available():
            self.model = self.model.to("cuda")
        self.embeddings = self._load_embeddings(file_path) if file_path else {}
        self.metadata = self._load_metadata(file_path) if file_path else {}
        self.similarity_threshold = similarity_threshold

    def _load_embeddings(self, file_path: str):
        with open(file_path, "r") as f:
            data = json.load(f)

        embeddings: dict = {}
        for section, items in data.items():
            embeddings[section] = []
            for item in items:
                main_text = item["text"]
                all_texts = [main_text] + item.get("synonyms", [])
                for text in all_texts:
                    embedding = self.model.encode(text, convert_to_tensor=True)
                    if torch.cuda.is_available() and isinstance(
                        embedding, torch.Tensor
                    ):
                        embedding = embedding.to("cuda")
                    embeddings[section].append((main_text, text, embedding))
        return embeddings

    @staticmethod
    def _load_metadata(file_path: str):
        with open(file_path, "r") as f:
            data = json.load(f)

        metadata: dict = {}
        for section, items in data.items():
            metadata[section] = {}
            for item in items:
                main_text = item["text"]
                meta = {
                    k: v for k, v in item.items() if k != "text" and k != "synonyms"
                }
                metadata[section][main_text] = meta
        return metadata

    @staticmethod
    def _measure_similarity(embedding1, embedding2):
        return util.pytorch_cos_sim(embedding1, embedding2).item()

    def check_for_best_matching_synonym(
        self,
        message: str,
        show_details: bool = False,
        labels: Optional[list] = None,
    ) -> tuple[str | None, dict]:
        start_time = time.time()
        input_embedding = self.model.encode(message, convert_to_tensor=True)
        if torch.cuda.is_available() and isinstance(input_embedding, torch.Tensor):
            input_embedding = input_embedding.to("cuda")

        max_similarity = -1
        best_match = None
        best_synonym = None
        text_metadata = {}

        categories = labels if labels else self.embeddings.keys()

        for category in categories:
            items = self.embeddings.get(category, [])
            metadata_items = self.metadata.get(category, {})
            for main_text, text, embedding in items:
                similarity = self._measure_similarity(input_embedding, embedding)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_match = main_text
                    best_synonym = text
                    text_metadata = metadata_items.get(main_text, {})

        end_time = time.time()
        inference_time = end_time - start_time

        if show_details:
            print(
                f"Input: <{message}> has match value <{max_similarity:.3f}> from matching with <{best_synonym}> for "
                f"original text: <{best_match}> with metadata {text_metadata} (exec.time: {inference_time:.4f})"
            )

        if max_similarity < self.similarity_threshold:
            return None, {}
        else:
            return best_match, text_metadata  # for now only stop commands use metadata


def main():
    matcher = SBERTMatcher(file_path=ROBEAU_PROMPTS)
    while True:
        message = input("Enter a message (or type 'exit' to quit): ")
        if message.lower() == "exit":
            break

        best_match, metadata = matcher.check_for_best_matching_synonym(
            message,
            show_details=True,
        )
        print(f"Best Match: {best_match}")
        print(f"Metadata: {metadata}\n")


if __name__ == "__main__":
    main()

import os

from src.config.settings import PROJECT_DIR_PATH

# Robeau specific paths
ROBEAU_DIR_PATH = os.path.join(PROJECT_DIR_PATH, "src/robeau")
ROBEAU_PROMPTS_JSON_FILE_PATH = os.path.join(
    PROJECT_DIR_PATH, "src/robeau/jsons/processed_for_robeau/robeau_prompts.json"
)
ROBEAU_RESPONSES_JSON_FILE_PATH = os.path.join(
    PROJECT_DIR_PATH, "src/robeau/jsons/processed_for_robeau/robeau_responses.json"
)

# Labels used for different types of nodes in the neo4j database
USER_LABELS = ["Prompt", "Whisper", "Plea", "Answer", "Greeting"]
ROBEAU_LABELS = ["Response", "Question", "Test"]
SYSTEM_LABELS = ["Input", "Output", "LogicGate", "TrafficGate"]

import os

from dotenv import load_dotenv

load_dotenv()

PROJECT_DIR_PATH = os.getenv("PROJECT_DIR_PATH")
VENV_PATH = os.getenv("VENV_PATH")
PYTHONPATH = os.getenv("PYTHONPATH")

GOOGLE_CLOUD_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY_PATH")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLOUD_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY_PATH")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

import os

from dotenv import load_dotenv

load_dotenv()


def get_env_var(var_name: str, default_value="MISSING_ENV_VAR") -> str:
    return str(os.getenv(var_name, default_value))


PROJECT_DIR_PATH = get_env_var("PROJECT_DIR_PATH")
VENV_PATH = get_env_var("VENV_PATH")
PYTHONPATH = get_env_var("PYTHONPATH")

GOOGLE_CLOUD_API_KEY = get_env_var("GOOGLE_CLOUD_API_KEY_PATH")

NEO4J_URI = get_env_var("NEO4J_URI")
NEO4J_USER = get_env_var("NEO4J_USER")
NEO4J_PASSWORD = get_env_var("NEO4J_PASSWORD")

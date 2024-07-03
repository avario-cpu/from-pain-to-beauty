import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_CLOUD_API_KEY_PATH')

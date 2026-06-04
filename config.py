"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN: str | None = os.environ.get("GITHUB_TOKEN")
SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
FLASK_ENV: str = os.environ.get("FLASK_ENV", "production")
SESSION_FILE_DIR: str = os.environ.get("SESSION_FILE_DIR", "./flask_session")
MAX_REPOS: int = 100       # Maximum repositories ceiling allowed per request
DEFAULT_LIMIT: int = 20

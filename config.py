"""
Configuration settings for Emoji Team Generator.
Loads environment variables and sets sensible application defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

# Load optional .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-emoji-secret-key-change-in-production-2026")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(INSTANCE_DIR / "emoji_team.db"))

    # Session cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1")

    # Participant cookie settings
    PARTICIPANT_COOKIE_NAME = "emoji_participant_token"
    PARTICIPANT_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days

    # Admin rate limit (per IP)
    ADMIN_RATE_LIMIT_MAX_ATTEMPTS = 5
    ADMIN_RATE_LIMIT_WINDOW_SECONDS = 300  # 5 minutes

    # Payload limit (1MB)
    MAX_CONTENT_LENGTH = 1024 * 1024

    # Initial admin from environment (optional auto-provisioning)
    INITIAL_ADMIN_USERNAME = os.environ.get("INITIAL_ADMIN_USERNAME")
    INITIAL_ADMIN_PASSWORD = os.environ.get("INITIAL_ADMIN_PASSWORD")

    # Curated Emoji Catalog
    CURATED_EMOJIS = [
        # Animals & Nature
        {"emoji": "🦁", "label": "Lion", "category": "Animals"},
        {"emoji": "🐯", "label": "Tiger", "category": "Animals"},
        {"emoji": "🐼", "label": "Panda", "category": "Animals"},
        {"emoji": "🦊", "label": "Fox", "category": "Animals"},
        {"emoji": "🐨", "label": "Koala", "category": "Animals"},
        {"emoji": "🐸", "label": "Frog", "category": "Animals"},
        {"emoji": "🐙", "label": "Octopus", "category": "Animals"},
        {"emoji": "🦋", "label": "Butterfly", "category": "Animals"},
        {"emoji": "🦄", "label": "Unicorn", "category": "Animals"},
        {"emoji": "🦉", "label": "Owl", "category": "Animals"},

        # Fun & Food
        {"emoji": "🍕", "label": "Pizza", "category": "Food"},
        {"emoji": "🍩", "label": "Donut", "category": "Food"},
        {"emoji": "🥑", "label": "Avocado", "category": "Food"},
        {"emoji": "🍓", "label": "Strawberry", "category": "Food"},
        {"emoji": "🍦", "label": "Ice Cream", "category": "Food"},
        {"emoji": "🌮", "label": "Taco", "category": "Food"},
        {"emoji": "🍔", "label": "Burger", "category": "Food"},
        {"emoji": "🍿", "label": "Popcorn", "category": "Food"},
        {"emoji": "🧁", "label": "Cupcake", "category": "Food"},
        {"emoji": "🍉", "label": "Watermelon", "category": "Food"},

        # Power & Cosmos
        {"emoji": "🚀", "label": "Rocket", "category": "Cosmic"},
        {"emoji": "⭐", "label": "Star", "category": "Cosmic"},
        {"emoji": "⚡", "label": "Lightning", "category": "Cosmic"},
        {"emoji": "🔥", "label": "Fire", "category": "Cosmic"},
        {"emoji": "🌈", "label": "Rainbow", "category": "Cosmic"},
        {"emoji": "💎", "label": "Diamond", "category": "Cosmic"},
        {"emoji": "🎯", "label": "Target", "category": "Cosmic"},
        {"emoji": "🎨", "label": "Palette", "category": "Cosmic"},
        {"emoji": "🎸", "label": "Guitar", "category": "Cosmic"},
        {"emoji": "🏆", "label": "Trophy", "category": "Cosmic"},

        # Characters & Magic
        {"emoji": "🤖", "label": "Robot", "category": "Fantasy"},
        {"emoji": "👾", "label": "Alien", "category": "Fantasy"},
        {"emoji": "🤠", "label": "Cowboy", "category": "Fantasy"},
        {"emoji": "🧙", "label": "Wizard", "category": "Fantasy"},
        {"emoji": "🥷", "label": "Ninja", "category": "Fantasy"},
        {"emoji": "🦸", "label": "Hero", "category": "Fantasy"},
        {"emoji": "👑", "label": "Crown", "category": "Fantasy"},
        {"emoji": "🔮", "label": "Crystal", "category": "Fantasy"},
        {"emoji": "🍀", "label": "Clover", "category": "Fantasy"},
        {"emoji": "🌻", "label": "Sunflower", "category": "Fantasy"},
    ]


class TestConfig(Config):
    """Configuration used during automated testing."""
    TESTING = True
    SECRET_KEY = "test-secret-key-12345"
    DATABASE_PATH = ":memory:"
    ADMIN_RATE_LIMIT_MAX_ATTEMPTS = 100

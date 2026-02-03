"""
Bot Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Telegram Proxy (for regions where Telegram is blocked)
# Format: http://user:pass@host:port or socks5://user:pass@host:port
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY", "")

# MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "premium_point_bot")

# Admin IDs (comma-separated in env)
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Key Generation
KEY_PREFIX = os.getenv("KEY_PREFIX", "PREM")
KEY_LENGTH = 16  # Total length of random part

# Loading defaults
DEFAULT_LOAD_PER_ROUND = 50
DEFAULT_DELAY_PER_ROUND = 210
DEFAULT_THREADS = 10
DEFAULT_TARGET_BALANCE = 200

# Instant delivery
DEFAULT_INSTANT_DELIVERY_RANGE_ENABLED = False
DEFAULT_INSTANT_DELIVERY_RANGE = 50

# Debug Mode
import sys
DEBUG = os.getenv("DEBUG", "False").lower() == "true" or "--debug" in sys.argv

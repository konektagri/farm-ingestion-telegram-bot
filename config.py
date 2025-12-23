"""Configuration and constants for the Telegram bot."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Validation
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing in .env file.")

# Conversation states
LANGUAGE, FARM_NUMBER, RAINFALL, RAINFALL_INTENSITY, SOIL_ROUGHNESS, GROWTH_STAGE, WATER_STATUS, OVERALL_HEALTH, VISIBLE_PROBLEMS, FERTILIZER, HERBICIDE, PESTICIDE, STRESS_EVENTS, LOCATION = range(14)

# File paths
PHOTOS_BASE_DIR = "farm_photos"
GEOJSON_PATH = "CambodiaProvinceBoundaries.geojson"

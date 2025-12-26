"""
Farm Photo Ingestion Telegram Bot with Google Drive Integration
Main entry point for the application.
"""
import logging
import math

# Telegram Imports
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ConversationHandler, CallbackQueryHandler
)

# Local imports
from config import (
    BOT_TOKEN, LANGUAGE, FARM_NUMBER, RAINFALL, RAINFALL_INTENSITY, 
    SOIL_ROUGHNESS, GROWTH_STAGE, WATER_STATUS, OVERALL_HEALTH, 
    VISIBLE_PROBLEMS, FERTILIZER, HERBICIDE, PESTICIDE, 
    STRESS_EVENTS, LOCATION
)
from handlers import (
    start, handle_language, handle_farm_number, handle_rainfall, 
    handle_rainfall_intensity, handle_soil_roughness, handle_growth_stage, 
    handle_water_status, handle_overall_health, handle_visible_problems, 
    handle_fertilizer, handle_fertilizer_type, handle_herbicide, 
    handle_pesticide, handle_stress_events, handle_location, cancel, 
    handle_add_new_farm, handle_photo, handle_help
)
from services.drive_service import get_drive_service

# --- CONFIGURATION & SETUP ---

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) using Haversine formula.
    Returns distance in Kilometers.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371  # Radius of earth in kilometers
    return c * r


def main():
    """Main function to start the bot."""
    # Initialize Drive service (validates configuration)
    drive_service = get_drive_service()
    
    print("🤖 Bot is starting...")
    print(f"☁️  Photos will be uploaded to Google Drive")
    print(f"📁 Parent Folder ID: {drive_service.parent_folder_id}")
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation handler for survey
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_new_farm)
        ],
        states={
            LANGUAGE: [CallbackQueryHandler(handle_language)],
            LOCATION: [MessageHandler(filters.LOCATION, handle_location)],
            FARM_NUMBER: [CallbackQueryHandler(handle_farm_number)],
            RAINFALL: [CallbackQueryHandler(handle_rainfall)],
            RAINFALL_INTENSITY: [CallbackQueryHandler(handle_rainfall_intensity)],
            SOIL_ROUGHNESS: [CallbackQueryHandler(handle_soil_roughness)],
            GROWTH_STAGE: [CallbackQueryHandler(handle_growth_stage)],
            WATER_STATUS: [CallbackQueryHandler(handle_water_status)],
            OVERALL_HEALTH: [CallbackQueryHandler(handle_overall_health)],
            VISIBLE_PROBLEMS: [CallbackQueryHandler(handle_visible_problems)],
            FERTILIZER: [
                CallbackQueryHandler(handle_fertilizer_type, pattern='^fert_type_'),
                CallbackQueryHandler(handle_fertilizer)
            ],
            HERBICIDE: [CallbackQueryHandler(handle_herbicide)],
            PESTICIDE: [CallbackQueryHandler(handle_pesticide)],
            STRESS_EVENTS: [CallbackQueryHandler(handle_stress_events)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", handle_help))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 Polling started.")
    application.run_polling()


if __name__ == '__main__':
    main()
"""
Farm Photo Ingestion Telegram Bot with Google Drive Integration
Main entry point for the application.
"""
import logging
import os
import asyncio
import math
from datetime import datetime
from dotenv import load_dotenv

# Telegram Imports
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ContextTypes, filters, ConversationHandler, CallbackQueryHandler
)

# Google Imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Local imports
from config import (
    BOT_TOKEN, LANGUAGE, FARM_NUMBER, RAINFALL, RAINFALL_INTENSITY, 
    SOIL_ROUGHNESS, GROWTH_STAGE, WATER_STATUS, OVERALL_HEALTH, 
    VISIBLE_PROBLEMS, FERTILIZER, HERBICIDE, PESTICIDE, 
    STRESS_EVENTS, LOCATION
)
from handlers import (
    start, handle_language, handle_farm_number, handle_rainfall, handle_rainfall_intensity,
    handle_soil_roughness, handle_growth_stage, handle_water_status,
    handle_overall_health, handle_visible_problems, handle_fertilizer,
    handle_fertilizer_type, handle_herbicide, handle_pesticide,
    handle_stress_events, handle_location, cancel, handle_add_new_farm
)

# --- CONFIGURATION & SETUP ---

# Load environment variables
load_dotenv()
PARENT_FOLDER_ID = os.getenv('PARENT_FOLDER_ID')
IMPERSONATED_USER_EMAIL = os.getenv('IMPERSONATED_USER_EMAIL')
SERVICE_ACCOUNT_FILE = 'secret/service_account.json'

# Validation
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing in .env file.")
if not PARENT_FOLDER_ID:
    raise ValueError("❌ PARENT_FOLDER_ID is missing in .env file.")
if not IMPERSONATED_USER_EMAIL:
    raise ValueError("❌ IMPERSONATED_USER_EMAIL is missing in .env file.")
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise ValueError(f"❌ {SERVICE_ACCOUNT_FILE} not found.")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- GOOGLE DRIVE HELPERS ---

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    """
    Authenticates using Domain-Wide Delegation to impersonate a specific user.
    """
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, 
        scopes=SCOPES
    )
    delegated_creds = creds.with_subject(IMPERSONATED_USER_EMAIL)
    return build('drive', 'v3', credentials=delegated_creds)

# Initialize Service Globally
DRIVE_SERVICE = get_drive_service()

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
    r = 6371 # Radius of earth in kilometers
    return c * r

def get_or_create_folder_sync(folder_name, parent_id):
    """Check if folder exists inside parent, if not create it."""
    try:
        query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = DRIVE_SERVICE.files().list(
            q=query, spaces='drive', fields='files(id, name)', 
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        
        folders = results.get('files', [])
        if folders:
            return folders[0]['id']
        
        # Create folder
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = DRIVE_SERVICE.files().create(
            body=file_metadata, fields='id', supportsAllDrives=True
        ).execute()
        return folder.get('id')
    except Exception as e:
        logger.error(f"Error finding/creating folder: {e}")
        raise

def upload_to_drive_sync(file_path, folder_path):
    """Blocking function to handle the actual upload logic. Supports nested folder paths."""
    try:
        # Handle nested folder paths (e.g., "2025-12-23/Phnom_Penh/Farm-01")
        folder_parts = folder_path.split('/')
        current_parent_id = PARENT_FOLDER_ID
        
        # Create each folder in the path
        for folder_name in folder_parts:
            current_parent_id = get_or_create_folder_sync(folder_name, current_parent_id)
        
        folder_id = current_parent_id
        
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(file_path, resumable=True)
        
        file = DRIVE_SERVICE.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True
        ).execute()
        
        return file.get('id'), file.get('webViewLink')
    except Exception as e:
        logger.error(f"Drive Upload Error: {e}")
        return None, None

def upload_csv_to_drive_sync(csv_file_path):
    """Upload CSV file to a 'Surveys' folder in Google Drive."""
    try:
        if not os.path.exists(csv_file_path):
            logger.error(f"CSV file not found: {csv_file_path}")
            return None, None
        
        # Create or get 'Surveys' folder
        folder_id = get_or_create_folder_sync('Surveys', PARENT_FOLDER_ID)
        
        # Check if file already exists in the folder
        filename = os.path.basename(csv_file_path)
        query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        results = DRIVE_SERVICE.files().list(
            q=query, spaces='drive', fields='files(id, name)',
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        
        existing_files = results.get('files', [])
        
        media = MediaFileUpload(csv_file_path, mimetype='text/csv', resumable=True)
        
        if existing_files:
            # Update existing file
            file_id = existing_files[0]['id']
            file = DRIVE_SERVICE.files().update(
                fileId=file_id,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()
            logger.info(f"Updated CSV file in Google Drive: {filename}")
        else:
            # Create new file
            file_metadata = {
                'name': filename,
                'parents': [folder_id],
                'mimeType': 'text/csv'
            }
            file = DRIVE_SERVICE.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()
            logger.info(f"Uploaded new CSV file to Google Drive: {filename}")
        
        return file.get('id'), file.get('webViewLink')
    except Exception as e:
        logger.error(f"CSV Drive Upload Error: {e}")
        return None, None

# --- MODIFIED PHOTO HANDLER FOR GOOGLE DRIVE ---

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo uploads and save to Google Drive instead of local storage."""
    user = update.effective_user
    from handlers import get_user_language
    lang = get_user_language(context)
    
    # Get the drive folder from user data (set during survey/location)
    drive_folder = context.user_data.get('drive_folder')
    survey_user_id = context.user_data.get('survey_user_id')
    
    # Validate that the current user is the one who completed the survey
    if survey_user_id and survey_user_id != user.id:
        await update.message.reply_text(
            "⚠️ You can only upload photos to your own surveys. Start a new survey with /start" if lang == 'en'
            else "⚠️ អ្នកអាចផ្ទុកឡើងរូបភាពទៅការស្ទង់មតិរបស់អ្នកប៉ុណ្ណោះ។ ចាប់ផ្តើមការស្ទង់មតិថ្មីជាមួយ /start"
        )
        return
    
    if not drive_folder:
        await update.message.reply_text(
            "⚠️ Please complete a survey first using /start" if lang == 'en' 
            else "⚠️ សូមបំពេញការស្ទង់មតិជាមុនសិនដោយប្រើ /start"
        )
        return
    
    if not update.message.photo:
        return

    status_msg = await update.message.reply_text("⏳ Processing image...")

    photo_obj = update.message.photo[-1]
    
    # Get metadata for descriptive filename: 2025-12-23_Province_User_Farm01_01.jpg
    date_str = context.user_data.get('date_str', datetime.now().strftime("%Y-%m-%d"))
    province = context.user_data.get('local_folder', 'Unknown')
    username = update.effective_user.username or update.effective_user.first_name or f"user_{update.effective_user.id}"
    username_clean = username.replace(" ", "_")
    farm_number = context.user_data.get('survey', {}).get('farm_number', '00')
    photo_count = context.user_data.get('photo_count', 0) + 1
    
    # Create filename: 2025-12-23_Province_User_Farm01_01.jpg
    filename = f"{date_str}_{province}_{username_clean}_Farm{int(farm_number):02d}_{photo_count:02d}.jpg"
    
    download_dir = "downloads"
    os.makedirs(download_dir, exist_ok=True)
    local_path = os.path.join(download_dir, filename)

    try:
        # Download photo from Telegram
        file = await context.bot.get_file(photo_obj.file_id)
        await file.download_to_drive(local_path)
        
        await status_msg.edit_text(f"⏳ Uploading to Cloud...")
        
        # Upload to Google Drive
        file_id = await asyncio.to_thread(
            upload_to_drive_sync, 
            local_path, 
            drive_folder
        )
        
        if file_id:
            # Increment photo count
            context.user_data['photo_count'] = context.user_data.get('photo_count', 0) + 1
            photo_count = context.user_data['photo_count']
            
            from handlers import get_text
            success_msg = get_text(
                lang, 'photo_saved',
                count=photo_count,
                folder=drive_folder
            )
            
            await status_msg.edit_text(success_msg)
            logger.info(f"User {user.id} uploaded photo #{photo_count} to {drive_folder} on Google Drive")
        else:
            from handlers import get_text
            await status_msg.edit_text(get_text(lang, 'error_saving'))

    except Exception as e:
        logger.error(f"Error in handle_photo: {e}")
        from handlers import get_text
        await status_msg.edit_text(get_text(lang, 'error_saving'))
        
    finally:
        # Clean up temporary file
        if os.path.exists(local_path):
            os.remove(local_path)

def main():
    """Main function to start the bot."""
    print("🤖 Bot is starting...")
    print(f"☁️  Photos will be uploaded to Google Drive")
    print(f"👤 Owner: {IMPERSONATED_USER_EMAIL}")
    print(f"📁 Parent Folder ID: {PARENT_FOLDER_ID}")
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation handler for survey
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_new_farm)
        ],
        states={
            LANGUAGE: [CallbackQueryHandler(handle_language)],
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
            LOCATION: [MessageHandler(filters.LOCATION, handle_location)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🚀 Polling started.")
    application.run_polling()

if __name__ == '__main__':
    main()
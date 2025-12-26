"""Photo upload handlers for Telegram bot."""
import os
import asyncio
import logging
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from translations import get_text, get_user_language
from services.drive_service import get_drive_service

logger = logging.getLogger(__name__)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo uploads and save to Google Drive instead of local storage."""
    user = update.effective_user
    lang = get_user_language(context)
    
    # Get the drive folder from user data (set during survey/location)
    drive_folder = context.user_data.get('drive_folder')
    survey_user_id = context.user_data.get('survey_user_id')
    
    # Validate that the current user is the one who completed the survey
    if survey_user_id and survey_user_id != user.id:
        await update.message.reply_text(get_text(lang, 'photo_own_survey_only'))
        return
    
    if not drive_folder:
        await update.message.reply_text(get_text(lang, 'complete_survey_first'))
        return
    
    if not update.message.photo:
        return

    photo_obj = update.message.photo[-1]
    
    # Get metadata for descriptive filename
    date_str = context.user_data.get('date_str', datetime.now().strftime("%Y-%m-%d"))
    province = context.user_data.get('local_folder', 'Unknown')
    username = user.username or user.first_name or f"user_{user.id}"
    username_clean = username.replace(" ", "_")
    farm_number = context.user_data.get('survey', {}).get('farm_number', '00')
    
    # Increment photo count immediately for user feedback
    current_count = context.user_data.get('photo_count', 0)
    next_photo_num = current_count + 1
    context.user_data['photo_count'] = next_photo_num
    
    # Create filename
    filename = f"{date_str}_{province}_{username_clean}_Farm{int(farm_number):02d}_{next_photo_num:02d}.jpg"
    
    download_dir = "downloads"
    os.makedirs(download_dir, exist_ok=True)
    local_path = os.path.join(download_dir, filename)

    # Show "Survey Another Farm" button immediately
    reply_markup = ReplyKeyboardMarkup(
        [[get_text(lang, 'add_new_farm')]],
        resize_keyboard=True
    )
    
    # Send immediate acknowledgment to user (don't make them wait)
    if next_photo_num == 1:
        instruction_msg = await update.message.reply_text(
            get_text(lang, 'continue_or_new'),
            reply_markup=reply_markup
        )
        context.user_data['photo_instruction_msg_id'] = instruction_msg.message_id
    
    # Download and upload in background task
    asyncio.create_task(
        _upload_photo_background(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            photo_file_id=photo_obj.file_id,
            local_path=local_path,
            drive_folder=drive_folder,
            user_id=user.id,
            photo_num=next_photo_num,
            lang=lang
        )
    )


async def _upload_photo_background(
    bot,
    chat_id: int,
    photo_file_id: str,
    local_path: str,
    drive_folder: str,
    user_id: int,
    photo_num: int,
    lang: str
) -> None:
    """
    Background task to download from Telegram and upload to Google Drive.
    
    This runs asynchronously so the user gets immediate response.
    Includes error notification to user if upload fails after retries.
    """
    try:
        logger.info(f"[Photo #{photo_num}] Starting download from Telegram: {photo_file_id}")
        
        # Download photo from Telegram
        file = await bot.get_file(photo_file_id)
        await file.download_to_drive(local_path)
        
        logger.info(f"[Photo #{photo_num}] Downloaded to: {local_path}")
        
        # Verify file exists after download
        import os
        if not os.path.exists(local_path):
            logger.error(f"[Photo #{photo_num}] File not found after download: {local_path}")
            await bot.send_message(chat_id=chat_id, text=get_text(lang, 'photo_upload_failed'))
            return
        
        file_size = os.path.getsize(local_path)
        logger.info(f"[Photo #{photo_num}] File size: {file_size} bytes")
        
        # Upload to Google Drive using service
        logger.info(f"[Photo #{photo_num}] Starting Drive upload to: {drive_folder}")
        drive_service = get_drive_service()
        result = await asyncio.to_thread(
            drive_service.upload_file, 
            local_path, 
            drive_folder
        )
        
        if result.success:
            logger.info(f"[Photo #{photo_num}] ✅ Upload successful! File ID: {result.file_id}")
        else:
            logger.warning(f"[Photo #{photo_num}] ❌ Upload failed: {result.error}")
            # Notify user of failure
            await bot.send_message(
                chat_id=chat_id,
                text=get_text(lang, 'photo_upload_failed')
            )

    except Exception as e:
        logger.error(f"[Photo #{photo_num}] ❌ Background error: {type(e).__name__}: {e}", exc_info=True)
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=get_text(lang, 'photo_upload_error')
            )
        except Exception:
            pass  # Don't fail if notification fails
        
    finally:
        # Clean up temporary file
        import os
        if os.path.exists(local_path):
            os.remove(local_path)
            logger.info(f"[Photo #{photo_num}] Cleaned up temp file: {local_path}")

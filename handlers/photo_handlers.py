"""Photo upload handlers for Telegram bot."""
import os
import asyncio
import logging
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from translations import get_text, get_user_language
from services.upload_queue import get_upload_queue, UploadTask

logger = logging.getLogger(__name__)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo uploads and queue them for Google Drive upload."""
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
    date_compact = date_str.replace("-", "")  # Convert 2025-12-26 to 20251226
    username = user.username or user.first_name or f"user_{user.id}"
    username_clean = username.replace(" ", "_")
    farm_number = context.user_data.get('survey', {}).get('farm_number', '00')
    
    # Get province code from context (set during survey)
    from constants import get_province_code
    province = context.user_data.get('province', 'Unknown')
    province_code = get_province_code(province)
    
    # Increment photo count immediately for user feedback
    current_count = context.user_data.get('photo_count', 0)
    next_photo_num = current_count + 1
    context.user_data['photo_count'] = next_photo_num
    
    # Create filename: CODE-surveyor-FarmNo_DATE_PhotoNo.jpg
    filename = f"{province_code}-{username_clean}-{int(farm_number):02d}_{date_compact}_{next_photo_num:02d}.jpg"
    
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
    
    # Create upload task and add to queue (sequential processing)
    upload_task = UploadTask(
        bot=context.bot,
        chat_id=update.effective_chat.id,
        photo_file_id=photo_obj.file_id,
        local_path=local_path,
        drive_folder=drive_folder,
        user_id=user.id,
        photo_num=next_photo_num,
        lang=lang
    )
    
    # Add to queue - this returns immediately, upload happens in background
    queue = get_upload_queue()
    await queue.add_task(upload_task)
    
    logger.info(f"[Photo #{next_photo_num}] Queued for upload to: {drive_folder}")

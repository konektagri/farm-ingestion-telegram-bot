"""Telegram bot handlers for farm photo ingestion."""
import logging
import os
import csv
import asyncio
from datetime import datetime
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, ConversationHandler

from config import LANGUAGE, FARM_NUMBER, RAINFALL, RAINFALL_INTENSITY, SOIL_ROUGHNESS, GROWTH_STAGE, WATER_STATUS, OVERALL_HEALTH, VISIBLE_PROBLEMS, FERTILIZER, HERBICIDE, PESTICIDE, STRESS_EVENTS, LOCATION, PHOTOS_BASE_DIR
from translations import get_text, get_user_language
from geo_utils import get_province_from_location

logger = logging.getLogger(__name__)

# Constants for survey image paths
SURVEY_IMAGES_DIR = Path('survey_images')
GROWTH_STAGE_IMAGES = {
    'land_prep': SURVEY_IMAGES_DIR / 'growth_land_prep.jpg',
    'transplanted': SURVEY_IMAGES_DIR / 'growth_transplanted.jpg',
    'tillering': SURVEY_IMAGES_DIR / 'growth_tillering.jpg',
    'flowering': SURVEY_IMAGES_DIR / 'growth_flowering.jpg',
    'ripening': SURVEY_IMAGES_DIR / 'growth_ripening.jpg',
    'harvest': SURVEY_IMAGES_DIR / 'growth_harvest.jpg',
    'fallow': SURVEY_IMAGES_DIR / 'growth_fallow.jpg',
}


def get_or_create_local_folder(date_str: str, folder_name: str) -> Path:
    """Create local folder if it doesn't exist and return the path."""
    folder_path = Path(PHOTOS_BASE_DIR) / date_str / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path


def build_inline_keyboard(buttons: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """Helper to build inline keyboard from list of (text, callback_data) tuples."""
    keyboard = [[InlineKeyboardButton(text, callback_data=data)] for text, data in buttons]
    return InlineKeyboardMarkup(keyboard)


def save_survey_to_csv(user_id: int, username: str, survey_data: dict, location_data: dict, date_str: str) -> None:
    """Save survey data to CSV file."""
    csv_file = Path('farm_surveys.csv')
    file_exists = csv_file.exists()
    
    # Prepare data row
    row = {
        'timestamp': datetime.now().isoformat(),
        'date': date_str,
        'user_id': user_id,
        'username': username,
        'farm_number': survey_data.get('farm_number', ''),
        'latitude': location_data.get('latitude', ''),
        'longitude': location_data.get('longitude', ''),
        'province': location_data.get('province', ''),
        'rainfall': survey_data.get('rainfall', ''),
        'rainfall_intensity': survey_data.get('rainfall_intensity', ''),
        'soil_roughness': survey_data.get('soil_roughness', ''),
        'growth_stage': survey_data.get('growth_stage', ''),
        'water_status': survey_data.get('water_status', ''),
        'overall_health': survey_data.get('overall_health', ''),
        'visible_problems': survey_data.get('visible_problems', ''),
        'fertilizer': survey_data.get('fertilizer', ''),
        'fertilizer_type': survey_data.get('fertilizer_type', ''),
        'herbicide': survey_data.get('herbicide', ''),
        'pesticide': survey_data.get('pesticide', ''),
        'stress_events': survey_data.get('stress_events', '')
    }
    
    # Write to CSV
    with open(csv_file, 'a', newline='', encoding='utf-8') as f:
        fieldnames = list(row.keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header if file is new
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(row)
    
    logger.info(f"Survey saved to CSV for user {user_id} in {location_data.get('province', 'Unknown')}")


async def handle_add_new_farm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Add New Farm' button to restart the survey."""
    # Check if the message text matches "Add New Farm" button in either language
    message_text = update.message.text if update.message else ""
    
    if "Add New Farm" in message_text or "Survey Another Farm" in message_text or "បន្ថែមចម្ការថ្មី" in message_text or "ស្ទង់ចម្ការផ្សេងទៀត" in message_text:
        # Clear previous survey data but keep language preference
        lang = context.user_data.get('language', 'en')
        context.user_data.clear()
        context.user_data['language'] = lang
        context.user_data['survey'] = {}
        
        # Build farm number keyboard (1-20)
        keyboard = []
        for i in range(1, 21, 4):  # 4 buttons per row
            row = [InlineKeyboardButton(str(num), callback_data=f"farm_{num}") for num in range(i, min(i+4, 21))]
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        farm_prompt = get_text(lang, 'farm_number_prompt')
        
        await update.message.reply_text(
            farm_prompt,
            reply_markup=reply_markup
        )
        return FARM_NUMBER
    
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start with language selection."""
    context.user_data.clear()
    context.user_data['survey'] = {}
    context.user_data['survey_user_id'] = update.effective_user.id  # Track user from the start
    
    keyboard = [
        [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
         InlineKeyboardButton("ខ្មែរ 🇰🇭", callback_data="lang_km")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Use welcome text from translations
    welcome_text = f"🌾 Farm Data Collection System\n\nWelcome, {update.effective_user.first_name}!\n\nYou are logged in as a field data collector.\n\nSelect your language to begin:\nសូមជ្រើសរើសភាសា:"
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup
    )
    return LANGUAGE


async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection and show farm number selection."""
    query = update.callback_query
    await query.answer()
    
    lang = query.data.replace("lang_", "")
    context.user_data['language'] = lang
    
    # Build farm number keyboard (1-20)
    keyboard = []
    for i in range(1, 21, 4):  # 4 buttons per row
        row = [InlineKeyboardButton(str(num), callback_data=f"farm_{num}") for num in range(i, min(i+4, 21))]
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    farm_prompt = get_text(lang, 'farm_number_prompt')
    
    await query.edit_message_text(
        farm_prompt,
        reply_markup=reply_markup
    )
    return FARM_NUMBER


async def handle_farm_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle farm number selection and start rainfall question."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    farm_num = query.data.replace("farm_", "")
    context.user_data['survey']['farm_number'] = farm_num
    
    # Show confirmation and start survey
    confirmation = get_text(lang, 'farm_selected', farm_number=farm_num)
    
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'yes'), callback_data="rainfall_yes"),
         InlineKeyboardButton(get_text(lang, 'no'), callback_data="rainfall_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        confirmation + "\n\n" + get_text(lang, 'rainfall_question'),
        reply_markup=reply_markup
    )
    return RAINFALL


async def handle_rainfall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle rainfall response."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    rainfall = query.data.replace("rainfall_", "")
    context.user_data['survey']['rainfall'] = rainfall
    
    # Build soil roughness keyboard (used in both branches)
    soil_keyboard = [
        [InlineKeyboardButton(get_text(lang, 'smooth'), callback_data="soil_smooth"),
         InlineKeyboardButton(get_text(lang, 'medium'), callback_data="soil_medium"),
         InlineKeyboardButton(get_text(lang, 'rough'), callback_data="soil_rough")]
    ]
    soil_reply_markup = InlineKeyboardMarkup(soil_keyboard)
    
    if rainfall == "yes":
        intensity_keyboard = [
            [InlineKeyboardButton(get_text(lang, 'heavy'), callback_data="intensity_heavy"),
             InlineKeyboardButton(get_text(lang, 'moderate'), callback_data="intensity_moderate"),
             InlineKeyboardButton(get_text(lang, 'low'), callback_data="intensity_low")]
        ]
        reply_markup = InlineKeyboardMarkup(intensity_keyboard)
        
        await query.edit_message_text(
            get_text(lang, 'rainfall_intensity'),
            reply_markup=reply_markup
        )
        return RAINFALL_INTENSITY
    else:
        # Skip to soil roughness
        context.user_data['survey']['rainfall_intensity'] = "N/A"
        await query.edit_message_text(
            get_text(lang, 'soil_roughness'),
            reply_markup=soil_reply_markup
        )
        return SOIL_ROUGHNESS


async def handle_rainfall_intensity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle rainfall intensity response."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    intensity = query.data.replace("intensity_", "")
    context.user_data['survey']['rainfall_intensity'] = intensity
    
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'smooth'), callback_data="soil_smooth"),
         InlineKeyboardButton(get_text(lang, 'medium'), callback_data="soil_medium"),
         InlineKeyboardButton(get_text(lang, 'rough'), callback_data="soil_rough")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        get_text(lang, 'soil_roughness'),
        reply_markup=reply_markup
    )
    return SOIL_ROUGHNESS


async def handle_soil_roughness(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle soil roughness response and show growth stages with images."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    soil = query.data.replace("soil_", "")
    context.user_data['survey']['soil_roughness'] = soil
    
    # Build growth stage keyboard
    growth_stages = [
        ('land_prep', '1️⃣'),
        ('transplanted', '2️⃣'),
        ('tillering', '3️⃣'),
        ('flowering', '4️⃣'),
        ('ripening', '5️⃣'),
        ('harvest', '6️⃣'),
        ('fallow', '7️⃣')
    ]
    
    keyboard = [
        [InlineKeyboardButton(f"{emoji} {get_text(lang, stage)}", callback_data=f"growth_{stage}")]
        for stage, emoji in growth_stages
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send media group with growth stage images
    try:
        media_group = []
        opened_files = []
        
        for stage, emoji in growth_stages:
            image_path = GROWTH_STAGE_IMAGES[stage]
            if image_path.exists():
                caption = f"{emoji} {get_text(lang, stage)}"
                file_obj = open(image_path, 'rb')
                opened_files.append(file_obj)
                media_group.append(
                    InputMediaPhoto(
                        file_obj,
                        caption=caption
                    )
                )
            else:
                logger.warning(f"Image not found: {image_path}")
        
        if media_group:
            # Delete the previous message
            await query.delete_message()
            
            # Send media group and store message IDs
            sent_messages = await query.message.reply_media_group(media=media_group)
            context.user_data['growth_stage_message_ids'] = [msg.message_id for msg in sent_messages]
            
            # Send growth stage question as a separate message
            question_msg = await query.message.reply_text(
                get_text(lang, 'growth_stage'),
                reply_markup=reply_markup
            )
            context.user_data['growth_stage_question_id'] = question_msg.message_id
        else:
            # Fallback if no images found
            await query.edit_message_text(
                get_text(lang, 'growth_stage'),
                reply_markup=reply_markup
            )
        
        # Close all opened files
        for file_obj in opened_files:
            file_obj.close()
            
    except Exception as e:
        logger.error(f"Error sending media group: {e}")
        # Ensure files are closed even on error
        for file_obj in opened_files:
            try:
                file_obj.close()
            except:
                pass
        # Fallback to text-only question
        await query.edit_message_text(
            get_text(lang, 'growth_stage'),
            reply_markup=reply_markup
        )
    
    return GROWTH_STAGE


async def handle_growth_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle growth stage response."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    growth = query.data.replace("growth_", "")
    context.user_data['survey']['growth_stage'] = growth
    
    water_statuses = [
        ('flooded', get_text(lang, 'flooded')),
        ('mostly_wet', get_text(lang, 'mostly_wet')),
        ('frequently_dry', get_text(lang, 'frequently_dry')),
        ('drought', get_text(lang, 'drought'))
    ]
    
    buttons = [(text, f"water_{status}") for status, text in water_statuses]
    reply_markup = build_inline_keyboard(buttons)
    
    # Delete the growth stage images
    chat_id = query.message.chat_id
    image_message_ids = context.user_data.get('growth_stage_message_ids', [])
    
    for msg_id in image_message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            logger.debug(f"Could not delete image message {msg_id}: {e}")
    
    # Delete the question message with keyboard
    try:
        await query.delete_message()
    except Exception as e:
        logger.debug(f"Could not delete question message: {e}")
    
    # Clean up stored message IDs
    context.user_data.pop('growth_stage_message_ids', None)
    context.user_data.pop('growth_stage_question_id', None)
    
    # Send the water status question as a new message
    await context.bot.send_message(
        chat_id=chat_id,
        text=get_text(lang, 'water_status'),
        reply_markup=reply_markup
    )
    
    return WATER_STATUS

async def handle_water_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle water status response and ask about overall health."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    water = query.data.replace("water_", "")
    context.user_data['survey']['water_status'] = water
    
    health_options = [
        ('excellent', get_text(lang, 'excellent')),
        ('good', get_text(lang, 'good')),
        ('fair', get_text(lang, 'fair')),
        ('poor', get_text(lang, 'poor'))
    ]
    
    buttons = [(text, f"health_{status}") for status, text in health_options]
    reply_markup = build_inline_keyboard(buttons)
    
    await query.edit_message_text(
        get_text(lang, 'overall_health'),
        reply_markup=reply_markup
    )
    return OVERALL_HEALTH


async def handle_overall_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle overall health response and ask about visible problems."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    health = query.data.replace("health_", "")
    context.user_data['survey']['overall_health'] = health
    context.user_data['survey']['visible_problems'] = []
    
    problem_options = [
        ('none_observed', 'None Observed'),
        ('yellowing', 'Yellowing'),
        ('brown_spots', 'Brown Spots'),
        ('wilting', 'Wilting'),
        ('lodging', 'Lodging'),
        ('pest_damage', 'Pest Damage'),
        ('weed_infestation', 'Weed Infestation'),
        ('uneven_growth', 'Uneven Growth'),
        ('other_problem', 'Other Problem')
    ]
    
    # Build keyboard with checkboxes
    keyboard = []
    selected = context.user_data['survey']['visible_problems']
    
    for problem, label in problem_options:
        checkbox = "✅" if problem in selected else "◻️"
        keyboard.append([
            InlineKeyboardButton(
                f"{checkbox} {get_text(lang, problem)}", 
                callback_data=f"problem_{problem}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            f"{get_text(lang, 'done_selecting')}", 
            callback_data="problem_done"
        )
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        get_text(lang, 'visible_problems'),
        reply_markup=reply_markup
    )
    return VISIBLE_PROBLEMS


async def handle_visible_problems(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle visible problems response (multi-select with checkbox UI)."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    problem = query.data.replace("problem_", "")
    
    if problem == "done":
        # Move to next question
        fertilizer_options = [
            (get_text(lang, 'fertilizer_yes'), 'fertilizer_yes'),
            (get_text(lang, 'fertilizer_no'), 'fertilizer_no'),
            (get_text(lang, 'fertilizer_dont_remember'), 'fertilizer_dont_remember')
        ]
        reply_markup = build_inline_keyboard(fertilizer_options)
        
        await query.edit_message_text(
            get_text(lang, 'fertilizer'),
            reply_markup=reply_markup
        )
        return FERTILIZER
    
    # Toggle problem selection
    problems = context.user_data['survey'].get('visible_problems', [])
    
    if problem == 'none_observed':
        # Clear all other selections if "none" is selected
        context.user_data['survey']['visible_problems'] = ['none_observed']
    else:
        # Remove "none" if other problems are selected
        if 'none_observed' in problems:
            problems.remove('none_observed')
        
        if problem in problems:
            problems.remove(problem)
        else:
            problems.append(problem)
        context.user_data['survey']['visible_problems'] = problems
    
    # Rebuild keyboard with updated checkboxes
    problem_options = [
        ('none_observed', 'None Observed'),
        ('yellowing', 'Yellowing'),
        ('brown_spots', 'Brown Spots'),
        ('wilting', 'Wilting'),
        ('lodging', 'Lodging'),
        ('pest_damage', 'Pest Damage'),
        ('weed_infestation', 'Weed Infestation'),
        ('uneven_growth', 'Uneven Growth'),
        ('other_problem', 'Other Problem')
    ]
    
    keyboard = []
    selected = context.user_data['survey']['visible_problems']
    
    for prob, label in problem_options:
        checkbox = "☑️" if prob in selected else "◻️"
        keyboard.append([
            InlineKeyboardButton(
                f"{checkbox} {get_text(lang, prob)}", 
                callback_data=f"problem_{prob}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            f"✅ {get_text(lang, 'done_selecting')}", 
            callback_data="problem_done"
        )
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update the message with new checkbox states
    await query.edit_message_reply_markup(reply_markup=reply_markup)
    
    return VISIBLE_PROBLEMS

async def handle_fertilizer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle fertilizer response."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    fertilizer = query.data.replace("fertilizer_", "")
    context.user_data['survey']['fertilizer'] = fertilizer
    
    if fertilizer == "yes":
        # Ask for fertilizer type
        type_options = [
            (get_text(lang, 'urea'), 'fert_type_urea'),
            (get_text(lang, 'npk'), 'fert_type_npk'),
            (get_text(lang, 'organic'), 'fert_type_organic'),
            (get_text(lang, 'other'), 'fert_type_other')
        ]
        reply_markup = build_inline_keyboard(type_options)
        
        await query.edit_message_text(
            get_text(lang, 'fertilizer_type'),
            reply_markup=reply_markup
        )
        return FERTILIZER
    else:
        # Skip to herbicide question
        context.user_data['survey']['fertilizer_type'] = 'N/A'
        herbicide_options = [
            (get_text(lang, 'herbicide_yes'), 'herbicide_yes'),
            (get_text(lang, 'herbicide_no'), 'herbicide_no'),
            (get_text(lang, 'herbicide_dont_remember'), 'herbicide_dont_remember')
        ]
        reply_markup = build_inline_keyboard(herbicide_options)
        
        await query.edit_message_text(
            get_text(lang, 'herbicide'),
            reply_markup=reply_markup
        )
        return HERBICIDE


async def handle_fertilizer_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle fertilizer type response."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    fert_type = query.data.replace("fert_type_", "")
    context.user_data['survey']['fertilizer_type'] = fert_type
    
    herbicide_options = [
        (get_text(lang, 'herbicide_yes'), 'herbicide_yes'),
        (get_text(lang, 'herbicide_no'), 'herbicide_no'),
        (get_text(lang, 'herbicide_dont_remember'), 'herbicide_dont_remember')
    ]
    reply_markup = build_inline_keyboard(herbicide_options)
    
    await query.edit_message_text(
        get_text(lang, 'herbicide'),
        reply_markup=reply_markup
    )
    return HERBICIDE


async def handle_herbicide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle herbicide response."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    herbicide = query.data.replace("herbicide_", "")
    context.user_data['survey']['herbicide'] = herbicide
    
    pesticide_options = [
        (get_text(lang, 'pesticide_yes'), 'pesticide_yes'),
        (get_text(lang, 'pesticide_no'), 'pesticide_no'),
        (get_text(lang, 'pesticide_dont_remember'), 'pesticide_dont_remember')
    ]
    reply_markup = build_inline_keyboard(pesticide_options)
    
    await query.edit_message_text(
        get_text(lang, 'pesticide'),
        reply_markup=reply_markup
    )
    return PESTICIDE


async def handle_pesticide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pesticide response."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    pesticide = query.data.replace("pesticide_", "")
    context.user_data['survey']['pesticide'] = pesticide
    
    stress_options = [
        (get_text(lang, 'flood'), 'stress_flood'),
        (get_text(lang, 'drought_event'), 'stress_drought_event'),
        (get_text(lang, 'none'), 'stress_none'),
        (get_text(lang, 'other_stress'), 'stress_other_stress')
    ]
    reply_markup = build_inline_keyboard(stress_options)
    
    await query.edit_message_text(
        get_text(lang, 'stress_events'),
        reply_markup=reply_markup
    )
    return STRESS_EVENTS


async def handle_stress_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle stress events response and show location button."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    stress = query.data.replace("stress_", "")
    context.user_data['survey']['stress_events'] = stress
    
    # Survey complete, show location button
    location_button = KeyboardButton(get_text(lang, 'share_location_btn'), request_location=True)
    reply_markup = ReplyKeyboardMarkup(
        [[location_button]], 
        resize_keyboard=True, 
        one_time_keyboard=True
    )
    
    await query.edit_message_text(
        get_text(lang, 'survey_complete')
    )
    
    await query.message.reply_text(
        get_text(lang, 'share_location'),
        reply_markup=reply_markup
    )
    
    return LOCATION


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle location sharing."""
    if not update.message or not update.message.location:
        lang = get_user_language(context)
        await update.message.reply_text(get_text(lang, 'use_button'))
        return LOCATION
    
    lang = get_user_language(context)
    user_loc = update.message.location
    context.user_data['location'] = user_loc
    context.user_data['survey_user_id'] = update.effective_user.id  # Track who completed the survey

    # Get current date
    date_str = datetime.now().strftime("%Y-%m-%d")
    context.user_data['date_str'] = date_str

    # Use geojson to detect province
    province = get_province_from_location(user_loc.latitude, user_loc.longitude)
    local_folder = province.replace(" ", "_") if province else "Unknown_Location"

    context.user_data['local_folder'] = local_folder
    context.user_data['province'] = province
    
    # Set Google Drive folder with user and farm number in nested format
    # Structure: date/province/user/farm
    username = update.effective_user.username or update.effective_user.first_name or f"user_{update.effective_user.id}"
    username_clean = username.replace(" ", "_")
    
    farm_number = context.user_data.get('survey', {}).get('farm_number', '0')
    farm_number_padded = f"Farm-{int(farm_number):02d}"
    drive_folder_path = f"{date_str}/{local_folder}/{username_clean}/{farm_number_padded}"
    context.user_data['drive_folder'] = drive_folder_path
    
    # Build and send survey summary
    survey = context.user_data.get('survey', {})
    
    # Helper function to translate survey values
    def translate_value(key: str) -> str:
        val = survey.get(key, 'N/A')
        if isinstance(val, list):
            return ', '.join([get_text(lang, v) for v in val]) if val else get_text(lang, 'none_observed')
        return get_text(lang, val) if val != 'N/A' else 'N/A'
    
    # Save survey data to CSV
    try:
        location_data = {
            'latitude': user_loc.latitude,
            'longitude': user_loc.longitude,
            'province': province
        }
        save_survey_to_csv(
            user_id=update.effective_user.id,
            username=update.effective_user.username or update.effective_user.first_name,
            survey_data=survey,
            location_data=location_data,
            date_str=date_str
        )
        
        # Upload CSV to Google Drive
        from main import upload_csv_to_drive_sync
        csv_path = 'farm_surveys.csv'
        file_id, web_link = await asyncio.to_thread(upload_csv_to_drive_sync, csv_path)
        if file_id:
            logger.info(f"CSV uploaded to Google Drive: {web_link}")
        else:
            logger.warning("Failed to upload CSV to Google Drive")
    except Exception as e:
        logger.error(f"Error saving survey to CSV: {e}", exc_info=True)
    
    # Comprehensive survey summary
    farm_number = survey.get('farm_number', 'N/A')
    survey_text = get_text(
        lang, 'survey_summary',
        farm_number=farm_number,
        province=province or 'Unknown',
        latitude=f"{user_loc.latitude:.6f}",
        longitude=f"{user_loc.longitude:.6f}",
        rainfall=translate_value('rainfall'),
        intensity=translate_value('rainfall_intensity'),
        soil=translate_value('soil_roughness'),
        growth=translate_value('growth_stage'),
        water=translate_value('water_status'),
        health=translate_value('overall_health'),
        problems=translate_value('visible_problems'),
        fertilizer=translate_value('fertilizer'),
        herbicide=translate_value('herbicide'),
        pesticide=translate_value('pesticide'),
        stress=translate_value('stress_events')
    )
    
    # Photo upload instructions with folder info
    photo_text = get_text(
        lang, 'photo_upload_instruction',
        farm_number=farm_number,
        province=province or 'Unknown',
        folder=drive_folder_path
    )
    
    # Send comprehensive summary
    await update.message.reply_text(
        survey_text + photo_text,
        reply_markup=ReplyKeyboardMarkup(
            [[get_text(lang, 'add_new_farm')]],
            resize_keyboard=True
        )
    )
    
    # Store photo count for tracking
    context.user_data['photo_count'] = 0
    
    logger.info(f"User {update.effective_user.id} completed survey for Farm #{farm_number} in {province} at {date_str}")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    lang = get_user_language(context)
    await update.message.reply_text(
        get_text(lang, 'cancel_msg'),
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo uploads."""
    if not update.message or not update.message.photo:
        return
    
    user = update.effective_user
    lang = get_user_language(context)
    
    # Check if location was set
    local_folder = context.user_data.get('local_folder')
    date_str = context.user_data.get('date_str')
    survey_user_id = context.user_data.get('survey_user_id')
    
    # Validate that the current user is the one who completed the survey
    if survey_user_id and survey_user_id != user.id:
        await update.message.reply_text(
            "⚠️ You can only upload photos to your own surveys. Start a new survey with /start" if lang == 'en'
            else "⚠️ អ្នកអាចផ្ទុកឡើងរូបភាពទៅការស្ទង់មតិរបស់អ្នកប៉ុណ្ណោះ។ ចាប់ផ្តើមការស្ទង់មតិថ្មីជាមួយ /start"
        )
        return
    
    if not local_folder or not date_str:
        await update.message.reply_text(get_text(lang, 'location_required'))
        return

    # User feedback
    status_msg = await update.message.reply_text(get_text(lang, 'processing'))

    # File setup
    photo_obj = update.message.photo[-1]  # Highest res
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = photo_obj.file_id[:8]
    filename = f"farm_{timestamp}_{unique_id}.jpg"
    
    # Create local folder path with date
    folder_path = get_or_create_local_folder(date_str, local_folder)
    local_path = folder_path / filename

    try:
        # Download from Telegram and save locally
        file = await context.bot.get_file(photo_obj.file_id)
        await file.download_to_drive(str(local_path))
        
        await status_msg.edit_text(
            get_text(lang, 'photo_saved')
        )
        logger.info(f"User {user.id} saved {filename} to {date_str}/{local_folder}")

    except Exception as e:
        logger.error(f"Error in handle_photo: {e}", exc_info=True)
        await status_msg.edit_text(get_text(lang, 'error_saving'))
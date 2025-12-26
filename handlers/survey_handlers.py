"""Survey conversation handlers for the Telegram bot."""
import logging
import asyncio
from datetime import datetime
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    LANGUAGE, FARM_NUMBER, RAINFALL, RAINFALL_INTENSITY, 
    SOIL_ROUGHNESS, GROWTH_STAGE, WATER_STATUS, OVERALL_HEALTH, 
    VISIBLE_PROBLEMS, FERTILIZER, HERBICIDE, PESTICIDE, 
    STRESS_EVENTS, LOCATION, PHOTOS_BASE_DIR
)
from constants import (
    RAINFALL_INTENSITY_OPTIONS, SOIL_OPTIONS, WATER_STATUS_OPTIONS,
    HEALTH_OPTIONS, YES_NO_REMEMBER_OPTIONS, FERTILIZER_TYPE_OPTIONS,
    STRESS_EVENT_OPTIONS, PROBLEM_NONE, VALUE_NA, get_province_code
)
from translations import get_text, get_user_language
from geo_utils import get_province_from_location
from handlers.keyboard_builders import (
    build_inline_keyboard, build_option_keyboard, build_soil_keyboard,
    build_farm_number_keyboard, build_growth_stage_keyboard,
    build_problems_keyboard, build_language_keyboard, build_yes_no_keyboard
)
from handlers.csv_handlers import save_and_upload_csv_background

logger = logging.getLogger(__name__)


# ==================== HELPER FUNCTIONS ====================

def get_callback_value(callback_data: str, prefix: str) -> str:
    """
    Extract the value from callback data by removing the prefix.
    
    Example: get_callback_value("rainfall_yes", "rainfall") returns "yes"
    """
    return callback_data.replace(f"{prefix}_", "")


def get_or_create_local_folder(date_str: str, folder_name: str) -> Path:
    """Create local folder if it doesn't exist and return the path."""
    folder_path = Path(PHOTOS_BASE_DIR) / date_str / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path

# ==================== ENTRY HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start with language selection."""
    context.user_data.clear()
    context.user_data['survey'] = {}
    context.user_data['survey_user_id'] = update.effective_user.id
    
    reply_markup = build_language_keyboard()
    
    await update.message.reply_text(
        "🌾 ប្រព័ន្ធប្រមូលទិន្នន័យស្រែ\nFarm Data Collection System\nជ្រើសរើសភាសាដើម្បីចាប់ផ្តើម:\nSelect your language to begin:",
        reply_markup=reply_markup
    )
    return LANGUAGE


async def handle_add_new_farm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Add New Farm' button to restart the survey from the beginning."""
    message_text = update.message.text if update.message else ""
    
    # Check if the message text matches "Add New Farm" button in either language
    add_new_farm_en = get_text('en', 'add_new_farm')
    add_new_farm_km = get_text('km', 'add_new_farm')
    
    if add_new_farm_en in message_text or add_new_farm_km in message_text:
        # Clear all previous data and start fresh (like /start)
        context.user_data.clear()
        context.user_data['survey'] = {}
        context.user_data['survey_user_id'] = update.effective_user.id
        
        reply_markup = build_language_keyboard()
        
        await update.message.reply_text(
            "🌾 ប្រព័ន្ធប្រមូលទិន្នន័យស្រែ\nFarm Data Collection System\nSelect your language to begin:\nជ្រើសរើសភាសាដើម្បីចាប់ផ្តើម:",
            reply_markup=reply_markup
        )
        return LANGUAGE
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    lang = get_user_language(context)
    await update.message.reply_text(
        get_text(lang, 'cancel_msg'),
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ==================== LANGUAGE & LOCATION HANDLERS ====================

async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection and request location."""
    query = update.callback_query
    await query.answer()
    
    lang = query.data.replace("lang_", "")
    context.user_data['language'] = lang
    
    # Request location instead of farm number
    location_button = KeyboardButton(
        get_text(lang, 'share_location_btn'),
        request_location=True
    )
    reply_markup = ReplyKeyboardMarkup(
        [[location_button]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    
    await query.edit_message_text(get_text(lang, 'language_selected'))
    await query.message.reply_text(
        get_text(lang, 'share_location'),
        reply_markup=reply_markup
    )
    return LOCATION


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle location sharing and show farm number selection."""
    if not update.message or not update.message.location:
        lang = get_user_language(context)
        await update.message.reply_text(get_text(lang, 'use_button'))
        return LOCATION
    
    lang = get_user_language(context)
    user_loc = update.message.location
    context.user_data['location'] = user_loc
    context.user_data['survey_user_id'] = update.effective_user.id

    # Get current date
    date_str = datetime.now().strftime("%Y-%m-%d")
    context.user_data['date_str'] = date_str

    # Use geojson to detect province
    province = get_province_from_location(user_loc.latitude, user_loc.longitude)
    local_folder = province.replace(" ", "_") if province else "Unknown_Location"

    context.user_data['local_folder'] = local_folder
    context.user_data['province'] = province
    
    farm_prompt = get_text(lang, 'farm_number_prompt')
    
    # First, remove the share_location keyboard and show farm prompt
    await update.message.reply_text(
        farm_prompt,
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Then send inline keyboard for farm selection
    await update.message.reply_text(
        get_text(lang, 'select_farm'),
        reply_markup=build_farm_number_keyboard()
    )
    return FARM_NUMBER


# ==================== SURVEY QUESTION HANDLERS ====================

async def handle_farm_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle farm number selection, setup drive folder, and start rainfall question."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    farm_num = query.data.replace("farm_", "")
    context.user_data['survey']['farm_number'] = farm_num
    
    # Set Google Drive folder with new structure:
    # Province Name/CODE-surveyor_name-FarmNo/YYYYMMDD
    province = context.user_data.get('province', 'Unknown')
    province_code = get_province_code(province)
    date_str = context.user_data.get('date_str', datetime.now().strftime("%Y-%m-%d"))
    date_compact = date_str.replace("-", "")  # Convert 2025-12-26 to 20251226
    username = update.effective_user.username or update.effective_user.first_name or f"user_{update.effective_user.id}"
    username_clean = username.replace(" ", "_")
    farm_number_padded = f"{int(farm_num):02d}"
    
    # New format: Province Name/CODE-surveyor-FarmNo/YYYYMMDD
    surveyor_folder = f"{province_code}-{username_clean}-{farm_number_padded}"
    drive_folder_path = f"{province}/{surveyor_folder}/{date_compact}"
    context.user_data['drive_folder'] = drive_folder_path
    
    # Show confirmation and start survey
    confirmation = get_text(lang, 'farm_selected', farm_number=farm_num)
    
    reply_markup = build_yes_no_keyboard(lang, 'rainfall')
    
    await query.edit_message_text(
        confirmation + "\n" + get_text(lang, 'rainfall_question'),
        reply_markup=reply_markup
    )
    return RAINFALL


async def handle_rainfall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle rainfall response."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    rainfall = get_callback_value(query.data, "rainfall")
    context.user_data['survey']['rainfall'] = rainfall
    
    if rainfall == "yes":
        # Ask about rainfall intensity
        reply_markup = build_option_keyboard(
            lang, RAINFALL_INTENSITY_OPTIONS, 'intensity', horizontal=True
        )
        await query.edit_message_text(
            get_text(lang, 'rainfall_intensity'),
            reply_markup=reply_markup
        )
        return RAINFALL_INTENSITY
    else:
        # Skip to soil roughness
        context.user_data['survey']['rainfall_intensity'] = VALUE_NA
        await query.edit_message_text(
            get_text(lang, 'soil_roughness'),
            reply_markup=build_soil_keyboard(lang)
        )
        return SOIL_ROUGHNESS


async def handle_rainfall_intensity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle rainfall intensity response."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    intensity = get_callback_value(query.data, "intensity")
    context.user_data['survey']['rainfall_intensity'] = intensity
    
    await query.edit_message_text(
        get_text(lang, 'soil_roughness'),
        reply_markup=build_soil_keyboard(lang)
    )
    return SOIL_ROUGHNESS


async def handle_soil_roughness(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle soil roughness response and show growth stages with images."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    soil = get_callback_value(query.data, "soil")
    context.user_data['survey']['soil_roughness'] = soil
    
    reply_markup = build_growth_stage_keyboard(lang)
    
    # Delete the old message and send a new photo message with growth stage reference
    growth_stage_image = Path("survey_images/rice_growth_stage.jpg")
    await query.message.delete()
    with open(growth_stage_image, 'rb') as photo:
        await query.message.chat.send_photo(
            photo=photo,
            caption=get_text(lang, 'growth_stage'),
            reply_markup=reply_markup
        )
    
    return GROWTH_STAGE


async def handle_growth_stage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle growth stage response."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    growth = get_callback_value(query.data, "growth")
    context.user_data['survey']['growth_stage'] = growth
    
    reply_markup = build_option_keyboard(lang, WATER_STATUS_OPTIONS, 'water')
    
    # Delete the photo message and send a new text message
    await query.message.delete()
    await query.message.chat.send_message(
        get_text(lang, 'water_status'),
        reply_markup=reply_markup
    )
    
    return WATER_STATUS


async def handle_water_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle water status response and ask about overall health."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    water = get_callback_value(query.data, "water")
    context.user_data['survey']['water_status'] = water
    
    reply_markup = build_option_keyboard(lang, HEALTH_OPTIONS, 'health')
    
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
    health = get_callback_value(query.data, "health")
    context.user_data['survey']['overall_health'] = health
    context.user_data['survey']['visible_problems'] = []
    
    reply_markup = build_problems_keyboard(lang, selected=[])
    
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
    problem = get_callback_value(query.data, "problem")
    
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
    
    if problem == PROBLEM_NONE:
        # Clear all other selections if "none" is selected
        context.user_data['survey']['visible_problems'] = [PROBLEM_NONE]
    else:
        # Remove "none" if other problems are selected
        if PROBLEM_NONE in problems:
            problems.remove(PROBLEM_NONE)
        
        if problem in problems:
            problems.remove(problem)
        else:
            problems.append(problem)
        context.user_data['survey']['visible_problems'] = problems
    
    # Rebuild keyboard with updated checkboxes
    selected = context.user_data['survey']['visible_problems']
    reply_markup = build_problems_keyboard(lang, selected)
    
    await query.edit_message_reply_markup(reply_markup=reply_markup)
    
    return VISIBLE_PROBLEMS


async def handle_fertilizer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle fertilizer response."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    fertilizer = get_callback_value(query.data, "fertilizer")
    context.user_data['survey']['fertilizer'] = fertilizer
    
    if fertilizer == "yes":
        # Ask for fertilizer type
        reply_markup = build_option_keyboard(
            lang, FERTILIZER_TYPE_OPTIONS, 'fert_type'
        )
        await query.edit_message_text(
            get_text(lang, 'fertilizer_type'),
            reply_markup=reply_markup
        )
        return FERTILIZER
    else:
        # Skip to herbicide question
        context.user_data['survey']['fertilizer_type'] = VALUE_NA
        reply_markup = build_option_keyboard(
            lang, YES_NO_REMEMBER_OPTIONS, 'herbicide', 'herbicide_'
        )
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
    fert_type = get_callback_value(query.data, "fert_type")
    context.user_data['survey']['fertilizer_type'] = fert_type
    
    reply_markup = build_option_keyboard(
        lang, YES_NO_REMEMBER_OPTIONS, 'herbicide', 'herbicide_'
    )
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
    herbicide = get_callback_value(query.data, "herbicide")
    context.user_data['survey']['herbicide'] = herbicide
    
    reply_markup = build_option_keyboard(
        lang, YES_NO_REMEMBER_OPTIONS, 'pesticide', 'pesticide_'
    )
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
    pesticide = get_callback_value(query.data, "pesticide")
    context.user_data['survey']['pesticide'] = pesticide
    
    reply_markup = build_option_keyboard(lang, STRESS_EVENT_OPTIONS, 'stress')
    await query.edit_message_text(
        get_text(lang, 'stress_events'),
        reply_markup=reply_markup
    )
    return STRESS_EVENTS


async def handle_stress_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle stress events response and complete the survey."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    stress = get_callback_value(query.data, "stress")
    context.user_data['survey']['stress_events'] = stress
    
    # Survey complete
    survey = context.user_data.get('survey', {})
    user_loc = context.user_data.get('location')
    province = context.user_data.get('province', 'Unknown')
    date_str = context.user_data.get('date_str', datetime.now().strftime("%Y-%m-%d"))
    
    # Prepare data for background task
    location_data = {
        'latitude': user_loc.latitude if user_loc else 0,
        'longitude': user_loc.longitude if user_loc else 0,
        'province': province
    }
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Run CSV save and Drive upload in background
    asyncio.create_task(
        save_and_upload_csv_background(
            user_id=user_id,
            username=username,
            survey_data=survey.copy(),
            location_data=location_data,
            date_str=date_str
        )
    )
    
    # Photo upload instructions
    photo_text = get_text(lang, 'photo_upload_instruction')
    
    # Send summary and photo instructions
    await query.edit_message_text(f"{photo_text}")
    
    # Store photo count for tracking
    context.user_data['photo_count'] = 0
    
    farm_number = survey.get('farm_number', 'N/A')
    logger.info(f"User {update.effective_user.id} completed survey for Farm #{farm_number} in {province} at {date_str}")
    return ConversationHandler.END

"""Keyboard builder functions for Telegram bot."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from constants import (
    FARM_NUMBER_MIN, FARM_NUMBER_MAX, FARM_BUTTONS_PER_ROW,
    PROBLEM_OPTIONS, SOIL_OPTIONS, GROWTH_STAGE_OPTIONS,
    CALLBACK_FARM, CALLBACK_GROWTH, CALLBACK_PROBLEM
)
from translations import get_text


def build_inline_keyboard(
    buttons: list[tuple[str, str]], 
    horizontal: bool = False
) -> InlineKeyboardMarkup:
    """
    Helper to build inline keyboard from list of (text, callback_data) tuples.
    
    Args:
        buttons: List of (display_text, callback_data) tuples
        horizontal: If True, place all buttons in one row; otherwise one per row
    
    Returns:
        InlineKeyboardMarkup
    """
    if horizontal:
        keyboard = [[InlineKeyboardButton(text, callback_data=data) for text, data in buttons]]
    else:
        keyboard = [[InlineKeyboardButton(text, callback_data=data)] for text, data in buttons]
    return InlineKeyboardMarkup(keyboard)


def build_option_keyboard(
    lang: str, 
    options: tuple, 
    prefix: str, 
    translation_prefix: str = '',
    horizontal: bool = False
) -> InlineKeyboardMarkup:
    """
    Generic helper to build option keyboards from a tuple of option keys.
    
    Args:
        lang: User language code
        options: Tuple of option keys (e.g., ('yes', 'no'))
        prefix: Callback data prefix (e.g., 'rainfall' -> 'rainfall_yes')
        translation_prefix: Optional prefix for translation keys (e.g., 'fertilizer_')
        horizontal: If True, place all buttons in one row
    
    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        (get_text(lang, f"{translation_prefix}{opt}"), f"{prefix}_{opt}")
        for opt in options
    ]
    return build_inline_keyboard(buttons, horizontal=horizontal)


def build_soil_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Build the soil roughness keyboard."""
    return build_option_keyboard(lang, SOIL_OPTIONS, 'soil', horizontal=True)


def build_farm_number_keyboard() -> InlineKeyboardMarkup:
    """Build the farm number selection keyboard."""
    keyboard = []
    for i in range(FARM_NUMBER_MIN, FARM_NUMBER_MAX + 1, FARM_BUTTONS_PER_ROW):
        row = [
            InlineKeyboardButton(str(num), callback_data=f"{CALLBACK_FARM}_{num}")
            for num in range(i, min(i + FARM_BUTTONS_PER_ROW, FARM_NUMBER_MAX + 1))
        ]
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


def build_growth_stage_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Build the growth stage selection keyboard with emoji icons."""
    keyboard = [
        [InlineKeyboardButton(
            f"{emoji} {get_text(lang, stage)}", 
            callback_data=f"{CALLBACK_GROWTH}_{stage}"
        )]
        for stage, emoji in GROWTH_STAGE_OPTIONS
    ]
    return InlineKeyboardMarkup(keyboard)


def build_problems_keyboard(lang: str, selected: list[str]) -> InlineKeyboardMarkup:
    """Build the visible problems multi-select keyboard with checkboxes."""
    keyboard = []
    for problem in PROBLEM_OPTIONS:
        checkbox = "☑️" if problem in selected else "◻️"
        keyboard.append([
            InlineKeyboardButton(
                f"{checkbox} {get_text(lang, problem)}",
                callback_data=f"{CALLBACK_PROBLEM}_{problem}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            f"✅ {get_text(lang, 'done_selecting')}",
            callback_data=f"{CALLBACK_PROBLEM}_done"
        )
    ])
    return InlineKeyboardMarkup(keyboard)


def build_language_keyboard() -> InlineKeyboardMarkup:
    """Build the language selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
         InlineKeyboardButton("ខ្មែរ 🇰🇭", callback_data="lang_km")]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_yes_no_keyboard(lang: str, prefix: str) -> InlineKeyboardMarkup:
    """Build a simple Yes/No keyboard."""
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'yes'), callback_data=f"{prefix}_yes"),
         InlineKeyboardButton(get_text(lang, 'no'), callback_data=f"{prefix}_no")]
    ]
    return InlineKeyboardMarkup(keyboard)

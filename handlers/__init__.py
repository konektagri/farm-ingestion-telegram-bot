"""Handler package for Telegram bot - modular handler organization."""

# Re-export all handlers for backward compatibility
from handlers.survey_handlers import (
    start,
    cancel,
    handle_add_new_farm,
    handle_language,
    handle_location,
    handle_farm_number,
    handle_rainfall,
    handle_rainfall_intensity,
    handle_soil_roughness,
    handle_growth_stage,
    handle_water_status,
    handle_overall_health,
    handle_visible_problems,
    handle_fertilizer,
    handle_fertilizer_type,
    handle_herbicide,
    handle_pesticide,
    handle_stress_events,
    get_callback_value,
)

from handlers.photo_handlers import (
    handle_photo,
)

from handlers.help_handler import (
    handle_help,
)

from handlers.csv_handlers import (
    save_survey_to_csv,
    save_and_upload_csv_background,
    set_upload_csv_fn,
)

from handlers.keyboard_builders import (
    build_inline_keyboard,
    build_option_keyboard,
    build_soil_keyboard,
    build_farm_number_keyboard,
    build_growth_stage_keyboard,
    build_problems_keyboard,
    build_language_keyboard,
    build_yes_no_keyboard,
)

# For backward compatibility with old import style
from translations import get_user_language

__all__ = [
    # Survey handlers
    'start',
    'cancel',
    'handle_add_new_farm',
    'handle_language',
    'handle_location',
    'handle_farm_number',
    'handle_rainfall',
    'handle_rainfall_intensity',
    'handle_soil_roughness',
    'handle_growth_stage',
    'handle_water_status',
    'handle_overall_health',
    'handle_visible_problems',
    'handle_fertilizer',
    'handle_fertilizer_type',
    'handle_herbicide',
    'handle_pesticide',
    'handle_stress_events',
    'get_callback_value',
    
    # Photo handlers
    'handle_photo',
    
    # Help handler
    'handle_help',
    
    # CSV handlers
    'save_survey_to_csv',
    'save_and_upload_csv_background',
    'set_upload_csv_fn',
    
    # Keyboard builders
    'build_inline_keyboard',
    'build_option_keyboard',
    'build_soil_keyboard',
    'build_farm_number_keyboard',
    'build_growth_stage_keyboard',
    'build_problems_keyboard',
    'build_language_keyboard',
    'build_yes_no_keyboard',
    
    # Utilities
    'get_user_language',
]

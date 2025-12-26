"""Centralized constants for the Telegram bot."""

# ==================== CALLBACK PREFIXES ====================
# Used to identify callback data from inline keyboards

CALLBACK_LANG = "lang"
CALLBACK_FARM = "farm"
CALLBACK_RAINFALL = "rainfall"
CALLBACK_INTENSITY = "intensity"
CALLBACK_SOIL = "soil"
CALLBACK_GROWTH = "growth"
CALLBACK_WATER = "water"
CALLBACK_HEALTH = "health"
CALLBACK_PROBLEM = "problem"
CALLBACK_FERTILIZER = "fertilizer"
CALLBACK_FERT_TYPE = "fert_type"
CALLBACK_HERBICIDE = "herbicide"
CALLBACK_PESTICIDE = "pesticide"
CALLBACK_STRESS = "stress"


# ==================== FARM CONFIGURATION ====================

FARM_NUMBER_MIN = 1
FARM_NUMBER_MAX = 20
FARM_BUTTONS_PER_ROW = 4


# ==================== SURVEY OPTIONS ====================

# Problem options for multi-select (used in visible_problems question)
PROBLEM_OPTIONS = (
    'none_observed',
    'yellowing',
    'brown_spots',
    'wilting',
    'lodging',
    'pest_damage',
    'weed_infestation',
    'uneven_growth',
    'other_problem',
)

# Rainfall intensity options
RAINFALL_INTENSITY_OPTIONS = ('heavy', 'moderate', 'low')

# Soil roughness options
SOIL_OPTIONS = ('smooth', 'medium', 'rough')

# Growth stage options with emoji indicators
GROWTH_STAGE_OPTIONS = (
    ('land_prep', '1️⃣'),
    ('transplanted', '2️⃣'),
    ('tillering', '3️⃣'),
    ('flowering', '4️⃣'),
    ('ripening', '5️⃣'),
    ('harvest', '6️⃣'),
    ('fallow', '7️⃣'),
)

# Water status options
WATER_STATUS_OPTIONS = ('flooded', 'mostly_wet', 'frequently_dry', 'drought')

# Overall health options
HEALTH_OPTIONS = ('excellent', 'good', 'fair', 'poor')

# Yes/No/Don't remember options (used for fertilizer, herbicide, pesticide)
YES_NO_REMEMBER_OPTIONS = ('yes', 'no', 'dont_remember')

# Fertilizer type options
FERTILIZER_TYPE_OPTIONS = ('urea', 'npk', 'organic', 'other')

# Stress event options
STRESS_EVENT_OPTIONS = ('flood', 'drought_event', 'none', 'other_stress')


# ==================== SPECIAL VALUES ====================

PROBLEM_DONE = "done"
PROBLEM_NONE = "none_observed"
VALUE_NA = "N/A"


# ==================== PROVINCE CODES ====================
# Cambodian province abbreviation codes for folder naming

PROVINCE_CODES = {
    'Banteay Meanchey': 'BMC',
    'Battambang': 'BTB',
    'Kampong Cham': 'KCM',
    'Kampong Chhnang': 'KCG',
    'Kampong Speu': 'KSP',
    'Kampong Thom': 'KTM',
    'Kampot': 'KPT',
    'Kandal': 'KDL',
    'Koh Kong': 'KKG',
    'Kratie': 'KTE',
    'Mondulkiri': 'MKR',
    'Oddar Meanchey': 'OMC',
    'Preah Vihear': 'PVH',
    'Pursat': 'PST',
    'Prey Veng': 'PVG',
    'Ratanakiri': 'RKP',
    'Siem Reap': 'SRP',
    'Stung Treng': 'STG',
    'Svay Rieng': 'SRG',
    'Takeo': 'TKO',
    'Kep': 'KEP',
    'Pailin': 'PLN',
    'Phnom Penh': 'PNH',
    'Sihanoukville': 'SHV',
    'Tbong Khmum': 'TBM',
}


def get_province_code(province_name: str) -> str:
    """
    Get the province abbreviation code for a given province name.
    
    Args:
        province_name: The full name of the province
        
    Returns:
        The 3-letter province code, or 'UNK' if not found
    """
    return PROVINCE_CODES.get(province_name, 'UNK')


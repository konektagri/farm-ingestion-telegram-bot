"""Translation module for multi-language support."""
import json
import os
from typing import Dict, Any

# Cache for loaded translations
_translations_cache: Dict[str, Dict[str, str]] = {}

def load_translations(language: str) -> Dict[str, str]:
    """Load translations for a specific language."""
    if language in _translations_cache:
        return _translations_cache[language]
    
    translations_dir = os.path.join(os.path.dirname(__file__))
    file_path = os.path.join(translations_dir, f"{language}.json")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
            _translations_cache[language] = translations
            return translations
    except FileNotFoundError:
        # Fallback to English if translation file not found
        if language != 'en':
            return load_translations('en')
        raise

def get_text(language: str, key: str, **kwargs) -> str:
    """
    Get translated text for a specific language and key.
    
    Args:
        language: Language code ('en', 'km')
        key: Translation key
        **kwargs: Format variables for the text
    
    Returns:
        Translated and formatted text
    """
    translations = load_translations(language)
    text = translations.get(key, key)
    return text.format(**kwargs) if kwargs else text

def get_user_language(context: Any) -> str:
    """Get user's preferred language from context."""
    return context.user_data.get('language', 'en')

"""Help command handler for Telegram bot."""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from translations import get_text, get_user_language

logger = logging.getLogger(__name__)


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command to show available commands and tips.
    
    Works both inside and outside of conversations.
    """
    lang = get_user_language(context)
    
    help_message = f"""
{get_text(lang, 'help_title')}

{get_text(lang, 'help_commands')}
• {get_text(lang, 'help_start')}
• {get_text(lang, 'help_cancel')}
• {get_text(lang, 'help_help')}

{get_text(lang, 'help_tips')}
{get_text(lang, 'help_tip_1')}
{get_text(lang, 'help_tip_2')}
{get_text(lang, 'help_tip_3')}
"""
    
    await update.message.reply_text(help_message.strip())
    logger.info(f"Help shown to user {update.effective_user.id}")

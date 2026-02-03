"""
Error handling for the bot.
"""
import logging
import traceback
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Log the full traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    logger.error(f"Traceback:\n{tb_string}")
    
    # Notify user if possible
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ <b>An error occurred</b>\n\n"
                "<i>Please try again later or contact support.</i>",
                parse_mode="HTML"
            )
        except Exception:
            pass  # Can't send message, ignore

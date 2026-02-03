"""
Settings management handlers.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from bot.core import BaseHandler, HandlerCategory, HandlerType
from bot.database import get_settings, update_settings
from bot.utils.keyboards import Keyboards
from bot.utils.formatters import Formatters

# Conversation states
WAITING_VALUE = 0


class SettingsHandler(BaseHandler):
    """View and modify bot settings."""
    
    command = "settings"
    description = "View/modify bot settings"
    category = HandlerCategory.ADMIN
    handler_type = HandlerType.CONVERSATION
    admin_only = True
    callback_patterns = [
        "settings_load_per_round", "settings_delay", "settings_threads",
        "settings_proxy", "settings_retry_same", "settings_halve",
        "settings_instant_range", "settings_toggle_", "settings_cancel"
    ]
    
    def get_conversation_handler(self) -> ConversationHandler:
        """Build conversation handler."""
        return ConversationHandler(
            entry_points=[
                CommandHandler("settings", self.wrap_handler(self.show_settings)),
                CallbackQueryHandler(self.wrap_handler(self.handle_setting_select), pattern="^settings_")
            ],
            states={
                WAITING_VALUE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.wrap_handler(self.receive_value)),
                    CallbackQueryHandler(self.wrap_handler(self.handle_setting_select), pattern="^settings_")
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel_callback, pattern="^settings_cancel$")
            ],
            per_user=True,
            per_chat=True
        )
    
    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current settings."""
        settings = await get_settings()
        text = Formatters.settings_display(settings) + "\n\n<i>Select a setting to modify:</i>"
        
        keyboard = Keyboards.settings_menu()
        
        if update.callback_query:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
        
        return ConversationHandler.END
    
    async def handle_setting_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle setting selection."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Toggle settings
        if data.startswith("settings_toggle_"):
            setting = data.replace("settings_toggle_", "")
            settings = await get_settings()
            current = settings.get(setting, False)
            await update_settings({setting: not current})
            await self.show_settings(update, context)
            return ConversationHandler.END
        
        # Boolean toggles
        if data == "settings_retry_same":
            settings = await get_settings()
            current = settings.get("retry_same_card", True)
            await update_settings({"retry_same_card": not current})
            await query.answer(f"Retry Same Card: {'ON' if not current else 'OFF'}", show_alert=True)
            await self.show_settings(update, context)
            return ConversationHandler.END
        
        if data == "settings_halve":
            settings = await get_settings()
            current = settings.get("retry_halve_on_failure", False)
            await update_settings({"retry_halve_on_failure": not current})
            await query.answer(f"Halve on Failure: {'ON' if not current else 'OFF'}", show_alert=True)
            await self.show_settings(update, context)
            return ConversationHandler.END
        
        # Value input settings
        setting_prompts = {
            "settings_load_per_round": ("load_per_round", "💰 <b>Enter new load per round amount</b> (5-100):"),
            "settings_delay": ("delay_per_round", "⏱ <b>Enter new delay between rounds</b> in seconds (150-600):"),
            "settings_threads": ("threads", "🧵 <b>Enter number of parallel loading threads</b> (1-20):\n\n<i>This is how many accounts will be loaded simultaneously per redemption.\nWhen one reaches the target, others are paused and saved.</i>"),
            "settings_proxy": ("proxy", "🌐 <b>Enter proxy URL</b> (or 'none' to disable):\n\n<b>Format:</b> http://user:pass@host:port"),
            "settings_instant_range": ("instant_delivery_range", "⚡ <b>Enter instant delivery range</b> (0-100):\n\n<i>0 = exact match only</i>")
        }
        
        if data in setting_prompts:
            setting_key, prompt = setting_prompts[data]
            context.user_data["editing_setting"] = setting_key
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="settings_cancel")]
            ])
            
            await query.message.edit_text(
                prompt,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return WAITING_VALUE
        
        return ConversationHandler.END
    
    async def receive_value(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive and validate new setting value."""
        setting_key = context.user_data.get("editing_setting")
        if not setting_key:
            await update.message.reply_text("❌ <b>No setting selected.</b>", parse_mode="HTML")
            return ConversationHandler.END
        
        value = update.message.text.strip()
        
        # Validation rules
        validators = {
            "load_per_round": (int, 5, 100),
            "delay_per_round": (int, 150, 600),
            "threads": (int, 1, 20),
            "instant_delivery_range": (int, 0, 100),
            "proxy": (str, None, None)
        }
        
        if setting_key in validators:
            val_type, min_val, max_val = validators[setting_key]
            
            try:
                if val_type == int:
                    value = int(value)
                    if min_val is not None and value < min_val:
                        await update.message.reply_text(f"❌ Value must be at least <b>{min_val}</b>", parse_mode="HTML")
                        return WAITING_VALUE
                    if max_val is not None and value > max_val:
                        await update.message.reply_text(f"❌ Value must be at most <b>{max_val}</b>", parse_mode="HTML")
                        return WAITING_VALUE
                elif val_type == str:
                    if value.lower() == "none":
                        value = ""
                    
                    # Enable/disable instant delivery range based on value
                    if setting_key == "instant_delivery_range":
                        await update_settings({"instant_delivery_range_enabled": value > 0})
                
            except ValueError:
                await update.message.reply_text("❌ <b>Invalid value.</b> Please enter a number.", parse_mode="HTML")
                return WAITING_VALUE
        
        # Update setting
        await update_settings({setting_key: value})
        
        await update.message.reply_text(
            f"✅ <b>Setting updated!</b>\n\n<b>{setting_key}</b> = <b>{value}</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ Back to Settings", callback_data="admin_settings")]
            ]),
            parse_mode="HTML"
        )
        
        context.user_data.pop("editing_setting", None)
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel editing."""
        context.user_data.pop("editing_setting", None)
        await update.message.reply_text(
            "❌ <i>Cancelled.</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ Back to Settings", callback_data="admin_settings")]
            ]),
            parse_mode="HTML"
        )
        return ConversationHandler.END
    
    async def cancel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel from callback."""
        query = update.callback_query
        await query.answer()
        context.user_data.pop("editing_setting", None)
        await self.show_settings(update, context)
        return ConversationHandler.END

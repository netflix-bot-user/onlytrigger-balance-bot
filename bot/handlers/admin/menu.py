"""
Admin menu handler.
"""
from telegram import Update
from telegram.ext import ContextTypes

from bot.core import BaseHandler, HandlerCategory, HandlerType
from bot.utils.keyboards import Keyboards
from bot.database import KeysDB, AccountsDB, InstantDeliveryDB, get_settings, update_settings


class AdminMenuHandler(BaseHandler):
    """Admin panel main menu."""
    
    command = "admin"
    description = "Open admin panel"
    category = HandlerCategory.ADMIN
    handler_type = HandlerType.COMMAND
    admin_only = True
    aliases = ["panel"]
    callback_patterns = ["admin_menu", "admin_keys", "admin_stock", "admin_instant", "admin_settings", "admin_analytics", "admin_toggle_pause"]
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin menu."""
        await self._show_menu(update, context)
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle menu navigation."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "admin_menu":
            await self._show_menu(update, context, edit=True)
        elif data == "admin_keys":
            await self._show_keys_menu(update, context)
        elif data == "admin_stock":
            await self._show_stock_menu(update, context)
        elif data == "admin_instant":
            await self._show_instant_menu(update, context)
        elif data == "admin_settings":
            await self._show_settings_menu(update, context)
        elif data == "admin_analytics":
            await self._show_analytics_menu(update, context)
        elif data == "admin_toggle_pause":
            await self._toggle_pause(update, context)
    
    async def _show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
        """Display the main admin menu."""
        # Get quick stats
        key_stats = await KeysDB.get_stats()
        stock_stats = await AccountsDB.get_stats()
        instant_stats = await InstantDeliveryDB.get_stats()
        settings = await get_settings()
        
        active_keys = key_stats.get('active', 0)
        stock_avail = stock_stats.get('available', 0)
        instant_avail = instant_stats.get('available', 0)
        is_paused = settings.get('paused', False)
        
        pause_status = "🔴 PAUSED" if is_paused else "🟢 Active"
        
        text = f"""🔐 <b>Admin Panel</b> [{pause_status}]

📊 <b>Quick Stats</b>

🔑 Active Keys: <b>{active_keys}</b>
📦 Stock: <b>{stock_avail}</b>
⚡ Instant: <b>{instant_avail}</b>

<i>Select an option below:</i>"""
        
        keyboard = Keyboards.admin_menu(is_paused=is_paused)
        
        if edit:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
    
    async def _show_keys_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show keys management menu."""
        stats = await KeysDB.get_stats()
        distribution = await KeysDB.get_balance_distribution()
        
        dist_text = ""
        if distribution:
            dist_text = "\n<b>💰 By Balance:</b>\n"
            for balance, count in sorted(distribution.items()):
                dist_text += f"   • ${balance}: <b>{count}</b>\n"
        
        text = f"""🔑 <b>Keys Management</b>

<b>📊 Statistics:</b>
   • 🟢 Active: <b>{stats.get('active', 0)}</b>
   • 🔴 Used: <b>{stats.get('used', 0)}</b>
   • 📊 Total: <b>{stats.get('total', 0)}</b>
{dist_text}
<i>Select an action:</i>"""
        
        keyboard = Keyboards.keys_menu()
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    
    async def _show_stock_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show stock management menu."""
        from bot.utils.formatters import Formatters
        
        stats = await AccountsDB.get_stats()
        text = Formatters.stock_stats(stats) + "\n\n<i>Select an action:</i>"
        
        keyboard = Keyboards.stock_menu()
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    
    async def _show_instant_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show instant delivery menu."""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from bot.utils.formatters import Formatters
        
        stats = await InstantDeliveryDB.get_stats()
        text = Formatters.instant_stats(stats) + "\n\n<i>Select an action:</i>"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 List Accounts", callback_data="instant_list"),
                InlineKeyboardButton("🗑 Clear Used", callback_data="instant_clear_used")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_menu")]
        ])
        
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    
    async def _show_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu."""
        from bot.database import get_settings
        from bot.utils.formatters import Formatters
        
        settings = await get_settings()
        text = Formatters.settings_display(settings) + "\n\n<i>Select a setting to modify:</i>"
        
        keyboard = Keyboards.settings_menu()
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    
    async def _show_analytics_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show analytics menu."""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from bot.utils.formatters import Formatters
        from bot.database import AnalyticsDB
        
        stats = await AnalyticsDB.get_overall_stats()
        text = Formatters.overall_analytics(stats) + "\n\n<i>Select for more details:</i>"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📅 Daily Stats", callback_data="analytics_daily"),
                InlineKeyboardButton("⏱ Load Times", callback_data="analytics_times")
            ],
            [
                InlineKeyboardButton("📊 Account Stats", callback_data="analytics_accounts")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_menu")]
        ])
        
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    
    async def _toggle_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle bot pause state."""
        settings = await get_settings()
        current = settings.get("paused", False)
        await update_settings({"paused": not current})
        
        status = "resumed" if current else "paused"
        await update.callback_query.answer(f"Bot {status}!", show_alert=True)
        await self._show_menu(update, context, edit=True)


class PauseHandler(BaseHandler):
    """Toggle bot pause state via command."""
    
    command = "pause"
    description = "Toggle bot pause (simulates no stock)"
    category = HandlerCategory.ADMIN
    handler_type = HandlerType.COMMAND
    admin_only = True
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle pause state."""
        settings = await get_settings()
        current = settings.get("paused", False)
        await update_settings({"paused": not current})
        
        if current:
            text = "▶️ <b>Bot Resumed</b>\n\nNew redemptions are now allowed."
        else:
            text = "⏸ <b>Bot Paused</b>\n\nNew redemptions will see 'No Stock'."
        
        await update.message.reply_text(text, parse_mode="HTML")

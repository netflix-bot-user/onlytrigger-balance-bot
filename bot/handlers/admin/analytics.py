"""
Analytics handlers.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.core import BaseHandler, HandlerCategory, HandlerType
from bot.database import AnalyticsDB, AccountsDB
from bot.utils.formatters import Formatters


class AnalyticsHandler(BaseHandler):
    """View analytics and statistics."""
    
    command = "stats"
    description = "View bot statistics"
    category = HandlerCategory.ADMIN
    handler_type = HandlerType.COMMAND
    admin_only = True
    aliases = ["analytics"]
    callback_patterns = ["analytics_daily", "analytics_times", "analytics_accounts", "analytics_overall"]
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        await self._show_overall(update, context)
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "analytics_overall":
            await self._show_overall(update, context, edit=True)
        elif data == "analytics_daily":
            await self._show_daily(update, context)
        elif data == "analytics_times":
            await self._show_load_times(update, context)
        elif data == "analytics_accounts":
            await self._show_account_stats(update, context)
    
    async def _show_overall(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        edit: bool = False
    ):
        """Show overall analytics."""
        stats = await AnalyticsDB.get_overall_stats()
        text = Formatters.overall_analytics(stats)
        
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
        
        if edit:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
    
    async def _show_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show daily statistics."""
        daily_stats = await AnalyticsDB.get_daily_stats(days=7)
        
        if not daily_stats:
            text = "📅 <b>Daily Statistics</b>\n\n<i>No data available yet.</i>"
        else:
            lines = ["📅 <b>Daily Statistics (Last 7 Days)</b>\n"]
            
            for day in daily_stats:
                date = day["date"]
                loads = day.get("loads", 0)
                success = day.get("successful_loads", 0)
                keys_gen = day.get("keys_generated", 0)
                keys_red = day.get("keys_redeemed", 0)
                
                lines.append(f"<b>{date}</b>")
                lines.append(f"   • Loads: <b>{success}/{loads}</b>")
                lines.append(f"   • Keys: <b>+{keys_gen}</b> / <b>-{keys_red}</b>")
                lines.append("")
            
            text = "\n".join(lines)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Back", callback_data="admin_analytics")]
        ])
        
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    
    async def _show_load_times(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show load time distribution."""
        distribution = await AnalyticsDB.get_load_time_distribution()
        
        if not distribution:
            text = "⏱ <b>Load Time Distribution</b>\n\n<i>No data available yet.</i>"
        else:
            lines = ["⏱ <b>Load Time Distribution</b>\n"]
            
            total = sum(distribution.values())
            for bucket, count in distribution.items():
                pct = (count / total * 100) if total > 0 else 0
                bar_len = int(pct / 5)
                bar = "▓" * bar_len + "░" * (20 - bar_len)
                lines.append(f"{bucket:>10} [{bar}] {count} ({pct:.1f}%)")
            
            text = "\n".join(lines)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Back", callback_data="admin_analytics")]
        ])
        
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    
    async def _show_account_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show account loading statistics."""
        analytics = await AccountsDB.get_load_analytics()
        text = Formatters.load_analytics(analytics)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Back", callback_data="admin_analytics")]
        ])
        
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )

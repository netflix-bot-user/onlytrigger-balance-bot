"""
Instant delivery management handlers.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.core import BaseHandler, HandlerCategory, HandlerType
from bot.database import InstantDeliveryDB
from bot.utils.formatters import Formatters


class InstantDeliveryHandler(BaseHandler):
    """Manage instant delivery accounts."""
    
    command = "instant"
    description = "Manage instant delivery"
    category = HandlerCategory.ADMIN
    handler_type = HandlerType.COMMAND
    admin_only = True
    callback_patterns = ["instant_list", "instant_clear_used", "instant_clear_all", "instant_view_", "instant_delete_", "instant_page_"]
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /instant command."""
        await self._show_stats(update, context)
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "instant_list":
            await self._show_list(update, context, page=0)
        
        elif data.startswith("instant_page_"):
            page = int(data.replace("instant_page_", ""))
            await self._show_list(update, context, page=page)
        
        elif data == "instant_clear_used":
            deleted = await InstantDeliveryDB.clear(used_only=True)
            await query.answer(f"✅ Cleared {deleted} used accounts", show_alert=True)
            await self._show_stats(update, context, edit=True)
        
        elif data == "instant_clear_all":
            deleted = await InstantDeliveryDB.clear(used_only=False)
            await query.answer(f"✅ Cleared {deleted} accounts", show_alert=True)
            await self._show_stats(update, context, edit=True)
        
        elif data.startswith("instant_view_"):
            account_id = data.replace("instant_view_", "")
            await self._show_account(update, context, account_id)
        
        elif data.startswith("instant_delete_"):
            account_id = data.replace("instant_delete_", "")
            await self._delete_account(update, context, account_id)
    
    async def _show_stats(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        edit: bool = False
    ):
        """Show instant delivery statistics."""
        stats = await InstantDeliveryDB.get_stats()
        text = Formatters.instant_stats(stats)
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 List Accounts", callback_data="instant_list"),
                InlineKeyboardButton("🗑 Clear Used", callback_data="instant_clear_used")
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
    
    async def _show_list(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        page: int = 0
    ):
        """Show paginated list of instant delivery accounts."""
        per_page = 8
        accounts = await InstantDeliveryDB.get_all(used=False, limit=per_page, skip=page * per_page)
        total = await InstantDeliveryDB.count(used=False)
        
        if not accounts:
            text = "📭 <i>No instant delivery accounts available.</i>"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back", callback_data="admin_instant")]
            ])
        else:
            lines = [f"⚡ <b>Instant Delivery Accounts</b> (Page {page + 1})\n"]
            
            for acc in accounts:
                balance = acc.get("balance", 0)
                original = acc.get("original_target", 0)
                lines.append(f"💰 <b>${balance}</b> (target was ${original})")
            
            text = "\n".join(lines)
            
            # Build keyboard
            buttons = []
            for acc in accounts:
                acc_id = str(acc["_id"])
                balance = acc.get("balance", 0)
                buttons.append([
                    InlineKeyboardButton(f"🔍 ${balance} Account", callback_data=f"instant_view_{acc_id}")
                ])
            
            # Pagination
            total_pages = (total + per_page - 1) // per_page
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️", callback_data=f"instant_page_{page - 1}"))
            nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("▶️", callback_data=f"instant_page_{page + 1}"))
            
            if nav_row:
                buttons.append(nav_row)
            
            buttons.append([InlineKeyboardButton("◀️ Back", callback_data="admin_instant")])
            keyboard = InlineKeyboardMarkup(buttons)
        
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    
    async def _show_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE, account_id: str):
        """Show account details."""
        account = await InstantDeliveryDB.get_by_id(account_id)
        
        if not account:
            await update.callback_query.message.edit_text(
                "❌ <b>Account not found.</b>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back", callback_data="instant_list")]
                ]),
                parse_mode="HTML"
            )
            return
        
        creds = Formatters.escape_html(account.get('credentials', 'N/A'))
        text = f"""⚡ <b>Instant Delivery Account</b>

💰 <b>Balance:</b> ${account.get('balance', 0)}
🎯 <b>Original Target:</b> ${account.get('original_target', 0)}
📅 <b>Added:</b> {Formatters.format_datetime(account.get('created_at'))}
📍 <b>Source:</b> {account.get('source', 'unknown')}

📋 <b>Credentials:</b>
{creds}"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Delete", callback_data=f"instant_delete_{account_id}")],
            [InlineKeyboardButton("◀️ Back", callback_data="instant_list")]
        ])
        
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    
    async def _delete_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE, account_id: str):
        """Delete an instant delivery account."""
        success = await InstantDeliveryDB.delete(account_id)
        
        if success:
            await update.callback_query.answer("✅ Account deleted!", show_alert=True)
        else:
            await update.callback_query.answer("❌ Failed to delete", show_alert=True)
        
        await self._show_list(update, context, page=0)

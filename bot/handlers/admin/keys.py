"""
Key management handlers.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from bot.core import BaseHandler, HandlerCategory, HandlerType
from bot.database import KeysDB, AnalyticsDB, AdminLogsDB, AdminAction
from bot.utils.keyboards import Keyboards
from bot.utils.formatters import Formatters
from bot.utils.notifications import AdminNotifier

# Conversation states
WAITING_BALANCE, WAITING_COUNT = range(2)


class GenKeyHandler(BaseHandler):
    """Generate redemption keys."""
    
    command = "genkey"
    description = "Generate redemption keys"
    category = HandlerCategory.ADMIN
    handler_type = HandlerType.COMMAND
    admin_only = True
    aliases = ["gk"]
    callback_patterns = ["keys_generate", "genkey_balance_", "genkey_count_"]
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /genkey command."""
        args = context.args
        
        if len(args) >= 1:
            # Direct command: /genkey 200 5
            try:
                balance = int(args[0])
                count = int(args[1]) if len(args) > 1 else 1
                
                if balance < 5 or balance > 500:
                    await update.message.reply_text("❌ <b>Invalid Balance</b>\n\nBalance must be between $5 and $500", parse_mode="HTML")
                    return
                
                if count < 1 or count > 100:
                    await update.message.reply_text("❌ <b>Invalid Count</b>\n\nCount must be between 1 and 100", parse_mode="HTML")
                    return
                
                await self._generate_keys(update, context, balance, count)
            except ValueError:
                await update.message.reply_text("❌ <b>Invalid Arguments</b>\n\nUsage: /genkey [balance] [count]", parse_mode="HTML")
        else:
            # Show balance selection
            await update.message.reply_text(
                "🔑 <b>Generate Keys</b>\n\n<i>Select target balance:</i>",
                reply_markup=Keyboards.balance_options("genkey_balance_"),
                parse_mode="HTML"
            )
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "keys_generate":
            await query.message.edit_text(
                "🔑 <b>Generate Keys</b>\n\n<i>Select target balance:</i>",
                reply_markup=Keyboards.balance_options("genkey_balance_"),
                parse_mode="HTML"
            )
        
        elif data.startswith("genkey_balance_"):
            balance = int(data.replace("genkey_balance_", ""))
            context.user_data["genkey_balance"] = balance
            
            await query.message.edit_text(
                f"🔑 <b>Generate Keys</b>\n\n💰 Balance: <b>${balance}</b>\n\n<i>Select count:</i>",
                reply_markup=Keyboards.count_options(f"genkey_count_"),
                parse_mode="HTML"
            )
        
        elif data.startswith("genkey_count_"):
            count = int(data.replace("genkey_count_", ""))
            balance = context.user_data.get("genkey_balance", 200)
            
            await self._generate_keys(update, context, balance, count, edit=True)
    
    async def _generate_keys(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        balance: int,
        count: int,
        edit: bool = False
    ):
        """Generate keys and display them."""
        user = update.effective_user
        user_id = user.id
        
        keys = await KeysDB.generate(
            target_balance=balance,
            count=count,
            created_by=user_id
        )
        
        # Log analytics and admin action
        for key in keys:
            await AnalyticsDB.log_key_generated(key, balance, user_id)
        
        await AdminLogsDB.log(
            action=AdminAction.KEY_GENERATE,
            admin_id=user_id,
            admin_username=user.username,
            details={"count": count, "target_balance": balance, "keys": keys},
            success=True
        )
        
        # Notify all admins
        await AdminNotifier.key_generated(
            admin_id=user_id,
            admin_username=user.username,
            count=count,
            target_balance=balance
        )
        
        # Format response
        if count == 1:
            text = f"✅ <b>Key Generated</b>\n\n🔑 {keys[0]}\n💰 Target: <b>${balance}</b>"
        else:
            keys_text = "\n".join([f"🔑 {k}" for k in keys])
            text = f"✅ <b>{count} Keys Generated</b>\n\n💰 Target: <b>${balance}</b>\n\n{keys_text}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Generate More", callback_data="keys_generate")],
            [InlineKeyboardButton("◀️ Back to Keys", callback_data="admin_keys")]
        ])
        
        if edit:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )


class ListKeysHandler(BaseHandler):
    """List and manage keys."""
    
    command = "listkeys"
    description = "List all keys"
    category = HandlerCategory.ADMIN
    handler_type = HandlerType.COMMAND
    admin_only = True
    aliases = ["keys"]
    callback_patterns = ["keys_list", "keys_page_", "keys_view_", "keys_delete_", "keys_filter_", "keys_stats"]
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /listkeys command."""
        await self._show_keys_list(update, context, page=0)
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "keys_list":
            await self._show_keys_list(update, context, page=0, edit=True)
        
        elif data.startswith("keys_page_"):
            page = int(data.replace("keys_page_", ""))
            await self._show_keys_list(update, context, page=page, edit=True)
        
        elif data.startswith("keys_view_"):
            key_id = data.replace("keys_view_", "")
            await self._show_key_details(update, context, key_id)
        
        elif data.startswith("keys_delete_"):
            key_id = data.replace("keys_delete_", "")
            await self._delete_key(update, context, key_id)
        
        elif data.startswith("keys_filter_"):
            status = data.replace("keys_filter_", "")
            status = status if status != "all" else None
            context.user_data["keys_filter"] = status
            await self._show_keys_list(update, context, page=0, edit=True)
        
        elif data == "keys_stats":
            await self._show_key_stats(update, context)
    
    async def _show_keys_list(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        page: int = 0,
        edit: bool = False
    ):
        """Show paginated keys list."""
        status_filter = context.user_data.get("keys_filter")
        per_page = 8
        
        keys = await KeysDB.get_all(status=status_filter, limit=per_page, skip=page * per_page)
        total = await KeysDB.count(status=status_filter)
        
        if not keys:
            text = "📭 <i>No keys found.</i>"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Generate Keys", callback_data="keys_generate")],
                [InlineKeyboardButton("◀️ Back", callback_data="admin_keys")]
            ])
        else:
            # Build list
            status_emoji = {"active": "🟢", "used": "🔴", "expired": "⚫"}
            lines = [f"📋 <b>Keys</b> (Page {page + 1})\n"]
            
            for key_doc in keys:
                status = key_doc.get("status", "unknown")
                emoji = status_emoji.get(status, "⚪")
                balance = key_doc.get("target_balance", 0)
                key_str = key_doc.get("key", "N/A")
                lines.append(f"{emoji} {key_str} — <b>${balance}</b>")
            
            text = "\n".join(lines)
            
            # Build keyboard
            buttons = []
            for key_doc in keys:
                key_id = str(key_doc["_id"])
                key_str = key_doc.get("key", "?")[-8:]  # Last 8 chars
                buttons.append([
                    InlineKeyboardButton(f"🔍 ...{key_str}", callback_data=f"keys_view_{key_id}")
                ])
            
            # Pagination
            total_pages = (total + per_page - 1) // per_page
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️", callback_data=f"keys_page_{page - 1}"))
            nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("▶️", callback_data=f"keys_page_{page + 1}"))
            
            if nav_row:
                buttons.append(nav_row)
            
            # Filter buttons
            buttons.append([
                InlineKeyboardButton("🟢 Active", callback_data="keys_filter_active"),
                InlineKeyboardButton("🔴 Used", callback_data="keys_filter_used"),
                InlineKeyboardButton("📊 All", callback_data="keys_filter_all")
            ])
            
            buttons.append([InlineKeyboardButton("◀️ Back", callback_data="admin_keys")])
            keyboard = InlineKeyboardMarkup(buttons)
        
        if edit:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
    
    async def _show_key_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, key_id: str):
        """Show details for a specific key."""
        key_doc = await KeysDB.get_by_id(key_id)
        
        if not key_doc:
            await update.callback_query.message.edit_text(
                "❌ <b>Key not found.</b>",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Back", callback_data="keys_list")
                ]]),
                parse_mode="HTML"
            )
            return
        
        text = Formatters.key_info(key_doc)
        
        buttons = []
        if key_doc.get("status") == "active":
            buttons.append([
                InlineKeyboardButton("🗑 Delete", callback_data=f"keys_delete_{key_id}")
            ])
        buttons.append([InlineKeyboardButton("◀️ Back", callback_data="keys_list")])
        
        await update.callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML"
        )
    
    async def _delete_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, key_id: str):
        """Delete a key."""
        success = await KeysDB.delete_by_id(key_id)
        
        if success:
            await update.callback_query.answer("✅ Key deleted!", show_alert=True)
        else:
            await update.callback_query.answer("❌ Failed to delete key", show_alert=True)
        
        await self._show_keys_list(update, context, page=0, edit=True)
    
    async def _show_key_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show key statistics."""
        stats = await KeysDB.get_stats()
        distribution = await KeysDB.get_balance_distribution()
        
        text = Formatters.key_stats(stats)
        
        if distribution:
            text += "\n\n<b>💰 Distribution by Balance:</b>"
            for balance, count in sorted(distribution.items()):
                text += f"\n   • ${balance}: <b>{count}</b>"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Back", callback_data="admin_keys")]
        ])
        
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )

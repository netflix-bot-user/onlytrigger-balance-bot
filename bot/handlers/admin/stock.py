"""
Stock management handlers.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from bot.core import BaseHandler, HandlerCategory, HandlerType
from bot.database import AccountsDB
from bot.utils.keyboards import Keyboards
from bot.utils.formatters import Formatters
from bot.utils.notifications import AdminNotifier

# Conversation states
WAITING_FILE = 0


class AddStockHandler(BaseHandler):
    """Add accounts to stock."""
    
    command = "addstock"
    description = "Add accounts to stock"
    category = HandlerCategory.ADMIN
    handler_type = HandlerType.CONVERSATION
    admin_only = True
    callback_patterns = ["stock_add", "stock_confirm_", "stock_cancel"]
    
    def get_conversation_handler(self) -> ConversationHandler:
        """Build conversation handler."""
        return ConversationHandler(
            entry_points=[
                CommandHandler("addstock", self.wrap_handler(self.start)),
                CallbackQueryHandler(self.wrap_handler(self.start_callback), pattern="^stock_add$")
            ],
            states={
                WAITING_FILE: [
                    MessageHandler(filters.Document.ALL, self.wrap_handler(self.receive_file)),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.wrap_handler(self.receive_text))
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel_callback, pattern="^stock_cancel$")
            ],
            per_user=True,
            per_chat=True
        )
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the add stock conversation."""
        await update.message.reply_text(
            "📤 <b>Add Stock</b>\n\n"
            "Send me accounts in one of these formats:\n"
            "• A .txt file with one account per line\n"
            "• Text message with accounts (one per line)\n\n"
            "<b>Format:</b> sess:xbc:uid:user_agent\n\n"
            "<i>Send /cancel to abort.</i>",
            parse_mode="HTML"
        )
        return WAITING_FILE
    
    async def start_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start from callback."""
        query = update.callback_query
        await query.answer()
        
        await query.message.edit_text(
            "📤 <b>Add Stock</b>\n\n"
            "Send me accounts in one of these formats:\n"
            "• A .txt file with one account per line\n"
            "• Text message with accounts (one per line)\n\n"
            "<b>Format:</b> sess:xbc:uid:user_agent\n\n"
            "<i>Send /cancel to abort.</i>",
            parse_mode="HTML"
        )
        return WAITING_FILE
    
    async def receive_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process uploaded file."""
        doc = update.message.document
        
        if not doc.file_name.endswith('.txt'):
            await update.message.reply_text(
                "❌ Please send a <b>.txt</b> file.",
                parse_mode="HTML"
            )
            return WAITING_FILE
        
        try:
            file = await doc.get_file()
            content = (await file.download_as_bytearray()).decode('utf-8')
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            
            # Validate format
            valid_lines = []
            for line in lines:
                parts = line.split(':')
                if len(parts) >= 4:
                    valid_lines.append(line)
            
            if not valid_lines:
                await update.message.reply_text(
                    "❌ <b>No valid accounts found in file.</b>\n\n"
                    "<b>Format:</b> sess:xbc:uid:user_agent",
                    parse_mode="HTML"
                )
                return WAITING_FILE
            
            # Add to database
            user = update.effective_user
            added = await AccountsDB.add_bulk(valid_lines, user.id)
            
            # Notify all admins
            if added > 0:
                await AdminNotifier.stock_added(
                    admin_id=user.id,
                    admin_username=user.username,
                    count=added
                )
            
            await update.message.reply_text(
                f"✅ <b>Stock Updated</b>\n\n"
                f"📥 Added: <b>{added}</b> accounts\n"
                f"⚠️ Skipped: <b>{len(lines) - added}</b> invalid lines",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 View Stock", callback_data="admin_stock")],
                    [InlineKeyboardButton("➕ Add More", callback_data="stock_add")]
                ]),
                parse_mode="HTML"
            )
            return ConversationHandler.END
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ <b>Error processing file:</b> {str(e)}",
                parse_mode="HTML"
            )
            return WAITING_FILE
    
    async def receive_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process text input."""
        text = update.message.text
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        # Validate format
        valid_lines = []
        for line in lines:
            parts = line.split(':')
            if len(parts) >= 4:
                valid_lines.append(line)
        
        if not valid_lines:
            await update.message.reply_text(
                "❌ <b>No valid accounts found.</b>\n\n"
                "<b>Format:</b> sess:xbc:uid:user_agent",
                parse_mode="HTML"
            )
            return WAITING_FILE
        
        # Add to database
        user = update.effective_user
        added = await AccountsDB.add_bulk(valid_lines, user.id)
        
        # Notify all admins
        if added > 0:
            await AdminNotifier.stock_added(
                admin_id=user.id,
                admin_username=user.username,
                count=added
            )
        
        await update.message.reply_text(
            f"✅ <b>Stock Updated</b>\n\n"
            f"📥 Added: <b>{added}</b> accounts\n"
            f"⚠️ Skipped: <b>{len(lines) - added}</b> invalid lines",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 View Stock", callback_data="admin_stock")],
                [InlineKeyboardButton("➕ Add More", callback_data="stock_add")]
            ]),
            parse_mode="HTML"
        )
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation."""
        await update.message.reply_text(
            "❌ <i>Cancelled.</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Back to Stock", callback_data="admin_stock")]
            ]),
            parse_mode="HTML"
        )
        return ConversationHandler.END
    
    async def cancel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel from callback."""
        query = update.callback_query
        await query.answer()
        await query.message.edit_text(
            "❌ <i>Cancelled.</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Back to Stock", callback_data="admin_stock")]
            ]),
            parse_mode="HTML"
        )
        return ConversationHandler.END


class StockHandler(BaseHandler):
    """View and manage stock."""
    
    command = "stock"
    description = "View stock status"
    category = HandlerCategory.ADMIN
    handler_type = HandlerType.COMMAND
    admin_only = True
    callback_patterns = ["stock_view", "stock_stats", "stock_clear", "stock_clear_confirm_", "stock_analytics"]
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stock command."""
        await self._show_stock_stats(update, context)
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "stock_view" or data == "stock_stats":
            await self._show_stock_stats(update, context, edit=True)
        
        elif data == "stock_clear":
            await self._show_clear_options(update, context)
        
        elif data.startswith("stock_clear_confirm_"):
            status = data.replace("stock_clear_confirm_", "")
            status = status if status != "all" else None
            await self._clear_stock(update, context, status)
        
        elif data == "stock_analytics":
            await self._show_analytics(update, context)
    
    async def _show_stock_stats(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        edit: bool = False
    ):
        """Show stock statistics."""
        stats = await AccountsDB.get_stats()
        text = Formatters.stock_stats(stats)
        
        keyboard = Keyboards.stock_menu()
        
        if edit:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
    
    async def _show_clear_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show clear stock options."""
        stats = await AccountsDB.get_stats()
        
        text = f"""🗑 <b>Clear Stock</b>

<b>Current stock:</b>
• 🟢 Available: <b>{stats.get('available', 0)}</b>
• 🔄 Processing: <b>{stats.get('processing', 0)}</b>
• ✅ Loaded: <b>{stats.get('loaded', 0)}</b>
• ❌ Failed: <b>{stats.get('failed', 0)}</b>

<i>What would you like to clear?</i>"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ Failed Only", callback_data="stock_clear_confirm_failed"),
                InlineKeyboardButton("✅ Loaded Only", callback_data="stock_clear_confirm_loaded")
            ],
            [
                InlineKeyboardButton("🟢 Available Only", callback_data="stock_clear_confirm_available")
            ],
            [
                InlineKeyboardButton("⚠️ Clear ALL", callback_data="stock_clear_confirm_all")
            ],
            [InlineKeyboardButton("◀️ Cancel", callback_data="admin_stock")]
        ])
        
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    
    async def _clear_stock(self, update: Update, context: ContextTypes.DEFAULT_TYPE, status: str = None):
        """Clear stock."""
        deleted = await AccountsDB.clear_all(status=status)
        
        status_text = status if status else "all"
        await update.callback_query.answer(f"✅ Cleared {deleted} {status_text} accounts", show_alert=True)
        
        await self._show_stock_stats(update, context, edit=True)
    
    async def _show_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show loading analytics."""
        analytics = await AccountsDB.get_load_analytics()
        text = Formatters.load_analytics(analytics)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Back", callback_data="admin_stock")]
        ])
        
        await update.callback_query.message.edit_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )

"""
Start and help handlers for users.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.core import BaseHandler, HandlerCategory, HandlerType
from bot.core.permissions import is_admin
from bot.utils.keyboards import Keyboards


class StartHandler(BaseHandler):
    """Handle /start command."""
    
    command = "start"
    description = "Start the bot"
    category = HandlerCategory.USER
    handler_type = HandlerType.COMMAND
    admin_only = False
    callback_patterns = ["user_menu", "user_redeem", "user_help", "user_support"]
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message."""
        if not update.message:
            return
            
        user = update.effective_user
        user_is_admin = await is_admin(user.id)
        
        text = f"""👋 <b>Welcome, {user.first_name}!</b>

🔐 <b>Premium Point</b>

Redeem keys for loaded accounts instantly."""
        
        await update.message.reply_text(
            text,
            reply_markup=Keyboards.user_menu(user_is_admin),
            parse_mode="HTML"
        )
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user menu callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = update.effective_user
        user_is_admin = await is_admin(user.id)
        
        if data == "user_menu":
            # Clear any pending states
            context.user_data.pop("awaiting_key", None)
            
            text = f"""👋 <b>Welcome, {user.first_name}!</b>

🔐 <b>Premium Point</b>

Redeem keys for loaded accounts instantly."""
            
            await query.message.edit_text(
                text,
                reply_markup=Keyboards.user_menu(user_is_admin),
                parse_mode="HTML"
            )
        
        elif data == "user_redeem":
            text = """🔑 <b>Redeem a Key</b>

Send your key now:"""
            
            await query.message.edit_text(
                text,
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
            
            # Set state to wait for key input
            context.user_data["awaiting_key"] = True
        
        elif data == "user_help":
            text = """📖 <b>How It Works</b>

<b>1.</b> Get a key from an authorized seller

<b>2.</b> Use /redeem to redeem your key

<b>3.</b> Receive your loaded account

<b>Delivery Types:</b>
• ⚡ <b>Instant</b> — Pre-loaded, delivered immediately
• 🔄 <b>Fresh</b> — Loaded on demand (1-5 min)

<b>Key Format:</b>
PREM-XXXX-XXXX-XXXX"""
            
            await query.message.edit_text(
                text,
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
        
        elif data == "user_support":
            text = """💬 <b>Support</b>

For assistance, contact the bot administrator.

<b>Common Issues:</b>
• Key not working → Check format & spelling
• Delivery delayed → Wait a few minutes
• Other issues → Contact support"""
            
            await query.message.edit_text(
                text,
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )


class HelpHandler(BaseHandler):
    """Handle /help command."""
    
    command = "help"
    description = "Show help message"
    category = HandlerCategory.USER
    handler_type = HandlerType.COMMAND
    admin_only = False
    callback_patterns = []
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message."""
        if not update.message:
            return
            
        user = update.effective_user
        user_is_admin = await is_admin(user.id)
        
        text = """📖 <b>How It Works</b>

<b>1.</b> Get a key from an authorized seller

<b>2.</b> Use /redeem to redeem your key

<b>3.</b> Receive your loaded account

<b>Delivery Types:</b>
• ⚡ <b>Instant</b> — Pre-loaded, delivered immediately
• 🔄 <b>Fresh</b> — Loaded on demand (1-5 min)

<b>Key Format:</b>
PREM-XXXX-XXXX-XXXX"""
        
        await update.message.reply_text(
            text,
            reply_markup=Keyboards.user_menu(user_is_admin),
            parse_mode="HTML"
        )

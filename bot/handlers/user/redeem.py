"""
Key redemption handler.
"""
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.core import BaseHandler, HandlerCategory, HandlerType
from bot.database import KeysDB, AccountsDB, InstantDeliveryDB, get_settings
from bot.loader.engine import get_loader_engine
from bot.utils.formatters import Formatters
from bot.utils.keygen import validate_key_format
from bot.utils.notifications import AdminNotifier
from bot.utils.keyboards import Keyboards
from bot.utils.refund import refund_key


class RedeemHandler(BaseHandler):
    """Handle key redemption."""
    
    command = "redeem"
    description = "Redeem a key"
    category = HandlerCategory.USER
    handler_type = HandlerType.COMMAND
    admin_only = False
    callback_patterns = ["redeem_confirm_", "redeem_cancel"]
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /redeem command or conversational key input."""
        # Guard: Only handle actual message commands
        if not update.message:
            return
        
        args = context.args
        key = None
        
        # Check if user sent key via conversation (awaiting_key state)
        if context.user_data.get("awaiting_key") and update.message.text:
            # Clear the state
            context.user_data["awaiting_key"] = False
            key = update.message.text.upper().strip()
        elif args:
            key = args[0].upper().strip()
        else:
            # No key provided - prompt for conversation flow
            await update.message.reply_text(
                "🔑 <b>Redeem a Key</b>\n\n"
                "Send your key now:",
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
            context.user_data["awaiting_key"] = True
            return
        
        # Validate format
        if not validate_key_format(key):
            await update.message.reply_text(
                "❌ <b>Invalid Format</b>\n\n"
                "Expected: PREM-XXXX-XXXX-XXXX",
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
            return
        
        # Check if key exists
        key_doc = await KeysDB.get_by_key(key)
        
        if not key_doc:
            await update.message.reply_text(
                "❌ <b>Key Not Found</b>\n\n"
                "Please check and try again.",
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
            return
        
        # Check key status
        status = key_doc.get("status")
        if status == "used":
            await update.message.reply_text(
                "❌ <b>Already Used</b>\n\n"
                "This key has been redeemed.",
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
            return
        elif status == "processing":
            await update.message.reply_text(
                "⏳ <b>In Progress</b>\n\n"
                "This key is being processed...",
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
            return
        elif status != "active":
            await update.message.reply_text(
                "❌ <b>Invalid Key</b>\n\n"
                "This key is no longer valid.",
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
            return
        
        # Process redemption
        user_id = update.effective_user.id
        target_balance = key_doc.get("target_balance", 0)
        
        # Check if bot is paused (simulates no stock)
        settings = await get_settings()
        if settings.get("paused", False):
            await update.message.reply_text(
                "❌ <b>No Stock</b>\n\n"
                "Try again later. Your key is still valid!",
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
            return
        
        # Check stock availability before processing
        stock_stats = await AccountsDB.get_stats()
        instant_stats = await InstantDeliveryDB.get_stats()
        
        stock_available = stock_stats.get('available', 0)
        instant_available = instant_stats.get('available', 0)
        
        if stock_available == 0 and instant_available == 0:
            await update.message.reply_text(
                "❌ <b>No Stock</b>\n\n"
                "Try again later. Your key is still valid!",
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
            return
        
        # ATOMIC CLAIM: Prevents double redemption race condition
        # This atomically checks status=active AND sets status=processing in one operation
        claimed_key = await KeysDB.claim_key(key, user_id)
        
        if not claimed_key:
            # Another request already claimed this key
            await update.message.reply_text(
                "⏳ <b>In Progress</b>\n\n"
                "This key is being processed.",
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
            return
        
        # Send initial processing message with nice UI
        processing_msg = await update.message.reply_text(
            Formatters.redemption_started(target_balance),
            parse_mode="HTML"
        )
        
        # Notify admins of redemption attempt
        username = update.effective_user.username
        await AdminNotifier.key_redeemed(user_id, username, key, target_balance)
        
        # Get loader engine
        engine = get_loader_engine()
        
        # Store start time
        import time
        start_time = time.time()
        context.user_data["redeem_start_time"] = start_time
        
        # Progress callback to update message every 10 seconds
        last_update_time = [0]
        last_balance = [0]
        last_status = ["Finding best account..."]
        
        async def progress_callback(status: str, balance: float, target: float, card_info: str = None):
            current_time = time.time()
            
            # Update stored values
            last_balance[0] = balance
            if status:
                last_status[0] = status
            
            # Rate limit updates to every 10 seconds
            if current_time - last_update_time[0] < 10:
                return
            
            last_update_time[0] = current_time
            elapsed = current_time - start_time
            
            text = Formatters.loading_progress(
                status=status,
                balance=balance,
                target=target,
                card_info=card_info,
                elapsed=elapsed
            )
            
            try:
                await processing_msg.edit_text(text, parse_mode="HTML")
            except Exception:
                pass  # Ignore edit errors
        
        # Process redemption
        try:
            result = await engine.process_redemption(
                target_balance=target_balance,
                user_id=user_id,
                key=key,
                progress_callback=progress_callback
            )
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
            
            await refund_key(
                key=key,
                target_balance=target_balance,
                message=processing_msg,
                reason=error_msg,
                elapsed=elapsed
            )
            return
        
        if result.get("success"):
            # Mark key as used
            await KeysDB.use_key(
                key=key,
                user_id=user_id,
                account_id=result.get("account_id", "")
            )
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Format delivery message
            delivery_text = Formatters.account_delivered(
                credentials=result.get("credentials", ""),
                balance=result.get("balance", 0),
                target=target_balance,
                instant=result.get("instant", False),
                duration=duration
            )
            
            # Delete processing message
            await processing_msg.delete()
            
            # Send delivery as new message (user gets notification)
            await context.bot.send_message(
                chat_id=user_id,
                text=delivery_text,
                parse_mode="HTML"
            )
            
            # Notify admins of successful delivery
            await AdminNotifier.delivery_success(
                user_id=user_id,
                username=username,
                key=key,
                balance=result.get("balance", 0),
                target=target_balance,
                instant=result.get("instant", False),
                duration=result.get("duration"),
                threads_used=result.get("threads_used")
            )
            
            # Check stock levels and notify if low
            stock_stats = await AccountsDB.get_stats()
            await AdminNotifier.stock_low(stock_stats.get("available", 0))
            
        else:
            error = result.get("error", "Unknown error")
            elapsed = time.time() - start_time
            
            # Determine reason
            if result.get("partial_balance"):
                reason = "Account saved for future orders."
            elif "No accounts available" in error:
                reason = "Out of stock. Try again later."
            else:
                reason = error[:100] + "..." if len(error) > 100 else error
            
            await refund_key(
                key=key,
                target_balance=target_balance,
                message=processing_msg,
                reason=reason,
                elapsed=elapsed,
                partial_balance=result.get("partial_balance")
            )
            
            # Notify admins of failed delivery
            await AdminNotifier.delivery_failed(
                user_id=user_id,
                username=username,
                key=key,
                target=target_balance,
                error=error,
                partial_balance=result.get("partial_balance")
            )
            
            # Check stock levels
            stock_stats = await AccountsDB.get_stats()
            await AdminNotifier.stock_low(stock_stats.get("available", 0))
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "redeem_cancel":
            await query.message.edit_text("❌ <i>Redemption cancelled.</i>", parse_mode="HTML")
    
    async def _delete_after_delay(self, message, delay: int):
        """Delete a message after a delay."""
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except Exception:
            pass  # Message may already be deleted

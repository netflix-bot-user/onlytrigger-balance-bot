"""
Universal key refund helper.
Handles key release, message formatting, and sending in one place.
"""
from typing import Optional, List, Dict, Any
from telegram import Message, Update, Bot
from telegram.ext import ContextTypes

from bot.utils.formatters import Formatters
from bot.utils.keyboards import Keyboards


async def refund_key(
    key: str,
    target_balance: float,
    message: Message,
    reason: str = None,
    elapsed: float = None,
    partial_balance: float = None,
    show_keyboard: bool = True
) -> bool:
    """
    Universal helper to refund a key and notify the user.
    
    Args:
        key: The key to refund
        target_balance: The target balance of the key
        message: The Telegram message to edit with refund info
        reason: Optional reason for the refund
        elapsed: Optional time elapsed in seconds
        partial_balance: Optional partial balance achieved
        show_keyboard: Whether to show the back keyboard
        
    Returns:
        True if refund was successful
    """
    # Lazy import to avoid circular dependency
    from bot.database import KeysDB
    
    # Release the key back to active
    released = await KeysDB.release_key(key)
    
    # Format the refund message
    text = Formatters.key_refunded(
        key=key,
        target_balance=target_balance,
        reason=reason,
        elapsed=elapsed,
        partial_balance=partial_balance
    )
    
    # Edit the message with refund info
    try:
        if show_keyboard:
            await message.edit_text(
                text,
                reply_markup=Keyboards.user_back(),
                parse_mode="HTML"
            )
        else:
            await message.edit_text(
                text,
                parse_mode="HTML"
            )
    except Exception:
        pass  # Message may have been deleted
    
    return released


async def refund_key_reply(
    key: str,
    target_balance: float,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    reason: str = None,
    elapsed: float = None,
    partial_balance: float = None
) -> bool:
    """
    Refund a key and send a new reply message (instead of editing).
    
    Args:
        key: The key to refund
        target_balance: The target balance of the key
        update: The Telegram update
        context: The bot context
        reason: Optional reason for the refund
        elapsed: Optional time elapsed in seconds
        partial_balance: Optional partial balance achieved
        
    Returns:
        True if refund was successful
    """
    # Lazy import to avoid circular dependency
    from bot.database import KeysDB
    
    # Release the key back to active
    released = await KeysDB.release_key(key)
    
    # Format the refund message
    text = Formatters.key_refunded(
        key=key,
        target_balance=target_balance,
        reason=reason,
        elapsed=elapsed,
        partial_balance=partial_balance
    )
    
    # Send new message
    try:
        await update.effective_message.reply_text(
            text,
            reply_markup=Keyboards.user_back(),
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    return released


async def notify_refund(
    bot: Bot,
    user_id: int,
    key: str,
    target_balance: float,
    reason: str = None
) -> bool:
    """
    Send a refund notification to a user (for bot restart/recovery scenarios).
    
    Args:
        bot: The Telegram bot instance
        user_id: The user's Telegram ID
        key: The key that was refunded
        target_balance: The target balance of the key
        reason: Optional reason for the refund
        
    Returns:
        True if notification was sent successfully
    """
    text = Formatters.key_refunded(
        key=key,
        target_balance=target_balance,
        reason=reason or "Bot was restarted during processing."
    )
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML"
        )
        return True
    except Exception:
        return False


async def recover_and_notify_stale_keys(bot: Bot) -> int:
    """
    Recover stale processing keys and notify users.
    Call this on bot startup.
    
    Args:
        bot: The Telegram bot instance
        
    Returns:
        Number of keys recovered and users notified
    """
    # Lazy import to avoid circular dependency
    from bot.database import KeysDB
    
    # Get all stale processing keys (processing for more than 30 minutes)
    stale_keys = await KeysDB.recover_stale_processing(minutes=30)
    
    notified = 0
    for key_doc in stale_keys:
        key = key_doc.get("key")
        target = key_doc.get("target_balance", 0)
        user_id = key_doc.get("claimed_by")
        
        if user_id:
            success = await notify_refund(
                bot=bot,
                user_id=user_id,
                key=key,
                target_balance=target,
                reason="Bot was restarted. Your key has been refunded."
            )
            if success:
                notified += 1
    
    return notified

"""
Admin notification system for important bot events.
"""
import logging
from typing import Optional, List
from datetime import datetime, timezone

from telegram import Bot
from telegram.constants import ParseMode

from bot.database import get_settings

logger = logging.getLogger(__name__)

# Global bot instance - set by main.py
_bot: Optional[Bot] = None


def set_bot(bot: Bot):
    """Set the bot instance for sending notifications."""
    global _bot
    _bot = bot


async def get_admin_ids() -> List[int]:
    """Get list of admin IDs from settings."""
    settings = await get_settings()
    return settings.get("admin_ids", [])


async def notify_admins(message: str, parse_mode: str = ParseMode.HTML):
    """
    Send a notification to all admins.
    
    Args:
        message: Message to send
        parse_mode: Parse mode for formatting
    """
    if not _bot:
        logger.warning("Bot not set for notifications")
        return
    
    admin_ids = await get_admin_ids()
    
    for admin_id in admin_ids:
        try:
            await _bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")


class AdminNotifier:
    """Helper class for sending formatted admin notifications."""
    
    @staticmethod
    async def key_redeemed(
        user_id: int,
        username: str,
        key: str,
        target_balance: float
    ):
        """Notify admins when a key is being redeemed."""
        msg = f"""🔑 <b>Redemption Started</b>

👤 {user_id} (@{username or 'N/A'})
🔑 {key}
💰 ${target_balance}"""
        
        await notify_admins(msg)
    
    @staticmethod
    async def delivery_success(
        user_id: int,
        username: str,
        key: str,
        balance: float,
        target: float,
        instant: bool,
        duration: float = None,
        threads_used: int = None
    ):
        """Notify admins of successful delivery."""
        delivery_type = "⚡ Instant" if instant else "🔄 Fresh"
        
        extra = []
        if duration:
            mins, secs = divmod(int(duration), 60)
            extra.append(f"⏱ {mins}m {secs}s")
        if threads_used and threads_used > 1:
            extra.append(f"🧵 {threads_used} threads")
        
        extra_str = " • ".join(extra)
        if extra_str:
            extra_str = f"\n{extra_str}"
        
        msg = f"""✅ <b>Delivered</b>

👤 {user_id} (@{username or 'N/A'})
{delivery_type} • ${balance} / ${target}{extra_str}"""
        
        await notify_admins(msg)
    
    @staticmethod
    async def delivery_failed(
        user_id: int,
        username: str,
        key: str,
        target: float,
        error: str,
        partial_balance: float = None
    ):
        """Notify admins of failed delivery."""
        partial_str = f" (partial: ${partial_balance})" if partial_balance else ""
        
        msg = f"""❌ <b>Failed</b>

👤 {user_id} (@{username or 'N/A'})
💰 ${target}{partial_str}
⚠️ {error}"""
        
        await notify_admins(msg)
    
    @staticmethod
    async def stock_low(available: int, threshold: int = 5):
        """Notify admins when stock is running low."""
        if available > threshold:
            return
        
        emoji = "🔴" if available == 0 else "🟡"
        
        msg = f"""{emoji} <b>Low Stock</b>

📦 {available} accounts remaining"""
        
        await notify_admins(msg)
    
    @staticmethod
    async def proxy_error(error: str):
        """Notify admins of proxy issues."""
        msg = f"""🌐 <b>Proxy Error</b>

{error}
<i>Loading paused to protect accounts.</i>"""
        
        await notify_admins(msg)
    
    @staticmethod
    async def key_generated(
        admin_id: int,
        admin_username: str,
        count: int,
        target_balance: float
    ):
        """Notify admins when keys are generated."""
        msg = f"""🔐 <b>Keys Generated</b>

👤 @{admin_username or admin_id}
{count}x ${target_balance}"""
        
        await notify_admins(msg)
    
    @staticmethod
    async def stock_added(
        admin_id: int,
        admin_username: str,
        count: int
    ):
        """Notify admins when stock is added."""
        msg = f"""📦 <b>Stock Added</b>

👤 @{admin_username or admin_id}
+{count} accounts"""
        
        await notify_admins(msg)

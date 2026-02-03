"""
Premium Point Bot - Main Entry Point

A Telegram bot for automated account loading with key-based redemption.
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.config import BOT_TOKEN, TELEGRAM_PROXY
from bot.core.registry import HandlerRegistry
from bot.database.mongo import connect_db, close_db
from bot.database import KeysDB, AccountsDB
from bot.handlers.system.errors import error_handler
from bot.loader.api import fetch_rules
from bot.utils.notifications import set_bot

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Initialize bot after startup."""
    logger.info("post_init: Starting initialization...")
    
    # Connect to database
    await connect_db()
    logger.info("post_init: Database connected")
    
    # Set bot instance for admin notifications
    set_bot(application.bot)
    logger.info("✓ Admin notifications enabled")
    
    # Recover stale processing states (from previous crash/restart)
    recovered_keys = await KeysDB.recover_stale_processing(timeout_minutes=10)
    recovered_accounts = await AccountsDB.recover_stale_processing(timeout_minutes=10)
    
    if recovered_keys:
        logger.info(f"✓ Recovered {len(recovered_keys)} stale keys → active")
        
        # Notify affected users with beautiful refund message
        from bot.utils.refund import notify_refund
        for key_doc in recovered_keys:
            user_id = key_doc.get("claimed_by")
            key = key_doc.get("key", "")
            target = key_doc.get("target_balance", 0)
            
            if user_id:
                try:
                    await notify_refund(
                        bot=application.bot,
                        user_id=user_id,
                        key=key,
                        target_balance=target,
                        reason="Bot was restarted. Your key has been refunded."
                    )
                except Exception as e:
                    logger.warning(f"Could not notify user {user_id}: {e}")
    
    if recovered_accounts > 0:
        logger.info(f"✓ Recovered {recovered_accounts} stale accounts → available")
    
    # Fetch dynamic rules for loader
    logger.info("post_init: About to call fetch_rules()...")
    rules_result = await fetch_rules()
    logger.info(f"post_init: fetch_rules() returned {rules_result}")
    if rules_result:
        logger.info("✓ Dynamic rules loaded")
    else:
        logger.warning("⚠ Could not fetch dynamic rules, using defaults")
    
    # Set bot commands for menu (with retry for network issues)
    registry: HandlerRegistry = application.bot_data.get("registry")
    if registry:
        user_commands = registry.get_bot_commands(include_admin=False)
        for attempt in range(3):
            try:
                await application.bot.set_my_commands(user_commands)
                logger.info(f"✓ Set {len(user_commands)} bot commands")
                break
            except Exception as e:
                if attempt < 2:
                    logger.warning(f"⚠ Failed to set commands (attempt {attempt + 1}): {e}")
                    import asyncio
                    await asyncio.sleep(2)
                else:
                    logger.error(f"✗ Could not set bot commands: {e}")


async def post_shutdown(application: Application):
    """Cleanup on shutdown."""
    await close_db()


def main():
    """Run the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set! Please set it in .env file")
        return
    
    # Build application with optional proxy
    builder = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .concurrent_updates(True)  # Allow handling multiple updates concurrently
    )
    
    # Configure proxy if set
    if TELEGRAM_PROXY:
        from telegram.request import HTTPXRequest
        
        # Determine proxy type
        if TELEGRAM_PROXY.startswith("socks"):
            # SOCKS proxy requires httpx[socks]
            logger.info(f"Using SOCKS proxy: {TELEGRAM_PROXY.split('@')[-1] if '@' in TELEGRAM_PROXY else TELEGRAM_PROXY}")
        else:
            logger.info(f"Using HTTP proxy: {TELEGRAM_PROXY.split('@')[-1] if '@' in TELEGRAM_PROXY else TELEGRAM_PROXY}")
        
        request = HTTPXRequest(
            proxy=TELEGRAM_PROXY,
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=30.0
        )
        builder = builder.request(request)
    
    application = builder.build()
    
    # Create handler registry
    registry = HandlerRegistry()
    
    # Discover and register handlers
    logger.info("Discovering handlers...")
    registry.discover("bot.handlers.admin")
    registry.discover("bot.handlers.user")
    
    logger.info("Registering handlers...")
    registry.register_all(application)
    
    # Add message handler for conversational key input
    from bot.handlers.user.redeem import RedeemHandler
    redeem_handler = RedeemHandler()
    
    async def handle_key_input(update: Update, context):
        """Handle text input when user is awaiting key."""
        if context.user_data.get("awaiting_key"):
            await redeem_handler.execute(update, context)
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_key_input
    ))
    
    # Store registry for later use
    application.bot_data["registry"] = registry
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    logger.info(f"✓ Registered {len(registry.handlers)} handlers")
    logger.info("Starting bot...")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

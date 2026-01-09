"""
Base Handler class with auto-registration support for commands, callbacks, and conversations.
"""
from abc import ABC
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes
)
from typing import List, Dict, Optional, Callable, Any
from enum import Enum

from .permissions import is_admin


class HandlerCategory(Enum):
    ADMIN = "admin"
    USER = "user"
    SYSTEM = "system"


class HandlerType(Enum):
    COMMAND = "command"
    CALLBACK = "callback"
    CONVERSATION = "conversation"


class BaseHandler(ABC):
    """
    Base class for all bot handlers.
    
    Supports:
    - Simple commands (/command)
    - Inline keyboard callbacks
    - Multi-step conversations
    - Automatic permission checks
    - Auto-registration
    """
    
    # Required - override in subclass
    command: Optional[str] = None
    description: Optional[str] = None
    category: Optional[HandlerCategory] = None
    handler_type: HandlerType = HandlerType.COMMAND
    
    # Permissions
    admin_only: bool = False
    
    # Optional
    aliases: List[str] = []
    callback_patterns: List[str] = []
    
    def __init__(self):
        self._app: Optional[Application] = None
    
    # ─────────────────────────────────────────────
    # Override these in subclasses
    # ─────────────────────────────────────────────
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Main command handler. Override this."""
        pass
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Inline keyboard callback handler. Override this."""
        pass
    
    def get_conversation_handler(self) -> Optional[ConversationHandler]:
        """Override to return a ConversationHandler for multi-step dialogs."""
        return None
    
    # ─────────────────────────────────────────────
    # Registration
    # ─────────────────────────────────────────────
    
    def register(self, app: Application) -> None:
        """Register this handler with the application."""
        self._app = app
        
        if self.handler_type == HandlerType.CONVERSATION:
            conv_handler = self.get_conversation_handler()
            if conv_handler:
                app.add_handler(conv_handler)
        
        elif self.handler_type == HandlerType.COMMAND:
            if self.command:
                app.add_handler(CommandHandler(self.command, self._wrap_execute()))
                for alias in self.aliases:
                    app.add_handler(CommandHandler(alias, self._wrap_execute()))
        
        # Register callbacks for all handler types (commands can have inline buttons too)
        for pattern in self.callback_patterns:
            app.add_handler(CallbackQueryHandler(
                self._wrap_callback(),
                pattern=f"^{pattern}"
            ))
    
    # ─────────────────────────────────────────────
    # Wrappers with permission checks
    # ─────────────────────────────────────────────
    
    def _wrap_execute(self) -> Callable:
        """Wrap execute with permission checks."""
        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if self.admin_only:
                user_id = update.effective_user.id
                if not await is_admin(user_id):
                    await update.message.reply_text("⛔ <b>Access Denied</b>\n\n<i>This command is for admins only.</i>", parse_mode="HTML")
                    return
            return await self.execute(update, context)
        return wrapped
    
    def _wrap_callback(self) -> Callable:
        """Wrap callback with permission checks."""
        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if self.admin_only:
                user_id = update.effective_user.id
                if not await is_admin(user_id):
                    await update.callback_query.answer("⛔ Admin only.", show_alert=True)
                    return
            return await self.callback(update, context)
        return wrapped
    
    def wrap_handler(self, func: Callable) -> Callable:
        """Utility to wrap any handler function with permission checks."""
        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if self.admin_only:
                user_id = update.effective_user.id
                if not await is_admin(user_id):
                    if update.message:
                        await update.message.reply_text("⛔ <b>Access Denied</b>\n\n<i>Admin only.</i>", parse_mode="HTML")
                    elif update.callback_query:
                        await update.callback_query.answer("⛔ Admin only.", show_alert=True)
                    return
            return await func(update, context)
        return wrapped

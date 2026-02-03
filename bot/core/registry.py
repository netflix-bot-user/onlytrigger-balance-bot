"""
Handler Registry - Auto-discovers and registers all handlers.
"""
import importlib
import pkgutil
from typing import List, Type, Optional
from telegram import BotCommand
from telegram.ext import Application

from .handler import BaseHandler, HandlerCategory


class HandlerRegistry:
    """
    Discovers and registers all handlers automatically.
    
    Usage:
        registry = HandlerRegistry()
        registry.discover("bot.handlers.admin")
        registry.discover("bot.handlers.user")
        registry.register_all(app)
    """
    
    def __init__(self):
        self.handlers: List[BaseHandler] = []
    
    def discover(self, package_path: str) -> None:
        """
        Scan a package for handler classes and instantiate them.
        
        Args:
            package_path: Dotted path to package (e.g., "bot.handlers.admin")
        """
        try:
            package = importlib.import_module(package_path)
        except ImportError as e:
            print(f"Warning: Could not import {package_path}: {e}")
            return
        
        if not hasattr(package, "__path__"):
            # It's a module, not a package
            self._scan_module(package)
            return
        
        for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
            full_module_path = f"{package_path}.{module_name}"
            
            if is_pkg:
                # Recursively discover in subpackages
                self.discover(full_module_path)
            else:
                try:
                    module = importlib.import_module(full_module_path)
                    self._scan_module(module)
                except ImportError as e:
                    print(f"Warning: Could not import {full_module_path}: {e}")
    
    def _scan_module(self, module) -> None:
        """Scan a module for BaseHandler subclasses."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # Check if it's a class, subclass of BaseHandler, not BaseHandler itself
            if (isinstance(attr, type) 
                and issubclass(attr, BaseHandler) 
                and attr is not BaseHandler
                and attr.command is not None):
                
                # Instantiate and add to handlers
                handler_instance = attr()
                self.handlers.append(handler_instance)
    
    def register_all(self, app: Application) -> None:
        """Register all discovered handlers with the application."""
        for handler in self.handlers:
            handler.register(app)
            print(f"  ✓ Registered: /{handler.command} ({handler.__class__.__name__})")
    
    def get_by_category(self, category: HandlerCategory) -> List[BaseHandler]:
        """Get all handlers in a specific category."""
        return [h for h in self.handlers if h.category == category]
    
    def get_bot_commands(self, include_admin: bool = False) -> List[BotCommand]:
        """
        Get list of BotCommand objects for Telegram command menu.
        
        Args:
            include_admin: Whether to include admin-only commands
        """
        commands = []
        for handler in self.handlers:
            if handler.command and handler.description:
                if handler.admin_only and not include_admin:
                    continue
                commands.append(BotCommand(handler.command, handler.description))
        return commands
    
    def get_admin_commands(self) -> List[BaseHandler]:
        """Get all admin-only handlers."""
        return [h for h in self.handlers if h.admin_only]
    
    def get_user_commands(self) -> List[BaseHandler]:
        """Get all user-accessible handlers."""
        return [h for h in self.handlers if not h.admin_only]

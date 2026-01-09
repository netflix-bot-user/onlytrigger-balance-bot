"""
Telegram inline keyboard builders.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any, Optional
import math


class Keyboards:
    """Factory for creating inline keyboards."""
    
    @staticmethod
    def user_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
        """Create the user main menu keyboard."""
        buttons = [
            [InlineKeyboardButton("🔑 Redeem Key", callback_data="user_redeem")],
            [
                InlineKeyboardButton("📖 How It Works", callback_data="user_help"),
                InlineKeyboardButton("💬 Support", callback_data="user_support")
            ]
        ]
        
        if is_admin:
            buttons.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_menu")])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def user_back() -> InlineKeyboardMarkup:
        """Back to user menu."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Back", callback_data="user_menu")]
        ])
    
    @staticmethod
    def confirm_cancel(
        confirm_callback: str,
        cancel_callback: str,
        confirm_text: str = "✅ Confirm",
        cancel_text: str = "❌ Cancel"
    ) -> InlineKeyboardMarkup:
        """Create a confirm/cancel keyboard."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(confirm_text, callback_data=confirm_callback),
                InlineKeyboardButton(cancel_text, callback_data=cancel_callback)
            ]
        ])
    
    @staticmethod
    def yes_no(
        yes_callback: str,
        no_callback: str
    ) -> InlineKeyboardMarkup:
        """Create a yes/no keyboard."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes", callback_data=yes_callback),
                InlineKeyboardButton("❌ No", callback_data=no_callback)
            ]
        ])
    
    @staticmethod
    def back_button(callback: str, text: str = "◀️ Back") -> InlineKeyboardMarkup:
        """Create a single back button."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(text, callback_data=callback)]
        ])
    
    @staticmethod
    def paginated_list(
        items: List[Dict[str, Any]],
        page: int,
        items_per_page: int,
        item_callback_prefix: str,
        page_callback_prefix: str,
        item_text_key: str = "text",
        item_id_key: str = "id",
        back_callback: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        """
        Create a paginated list keyboard.
        
        Args:
            items: List of items with text and id
            page: Current page (0-indexed)
            items_per_page: Items per page
            item_callback_prefix: Prefix for item callbacks (e.g., "key_view_")
            page_callback_prefix: Prefix for page callbacks (e.g., "keys_page_")
            item_text_key: Key in item dict for display text
            item_id_key: Key in item dict for ID
            back_callback: Optional back button callback
        """
        total_pages = max(1, math.ceil(len(items) / items_per_page))
        page = max(0, min(page, total_pages - 1))
        
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_items = items[start_idx:end_idx]
        
        keyboard = []
        
        # Item buttons
        for item in page_items:
            text = item.get(item_text_key, str(item.get(item_id_key, "?")))
            item_id = str(item.get(item_id_key, ""))
            keyboard.append([
                InlineKeyboardButton(text, callback_data=f"{item_callback_prefix}{item_id}")
            ])
        
        # Pagination row
        if total_pages > 1:
            nav_row = []
            
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    "◀️ Prev",
                    callback_data=f"{page_callback_prefix}{page - 1}"
                ))
            
            nav_row.append(InlineKeyboardButton(
                f"📄 {page + 1}/{total_pages}",
                callback_data="noop"
            ))
            
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton(
                    "Next ▶️",
                    callback_data=f"{page_callback_prefix}{page + 1}"
                ))
            
            keyboard.append(nav_row)
        
        # Back button
        if back_callback:
            keyboard.append([InlineKeyboardButton("◀️ Back", callback_data=back_callback)])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """Create the settings menu keyboard."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💰 Load Per Round", callback_data="settings_load_per_round"),
                InlineKeyboardButton("⏱ Delay", callback_data="settings_delay")
            ],
            [
                InlineKeyboardButton("🧵 Threads", callback_data="settings_threads"),
                InlineKeyboardButton("🌐 Proxy", callback_data="settings_proxy")
            ],
            [
                InlineKeyboardButton("🔄 Retry Same Card", callback_data="settings_retry_same"),
                InlineKeyboardButton("➗ Halve on Fail", callback_data="settings_halve")
            ],
            [
                InlineKeyboardButton("⚡ Instant Delivery Range", callback_data="settings_instant_range")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_menu")]
        ])
    
    @staticmethod
    def admin_menu(is_paused: bool = False) -> InlineKeyboardMarkup:
        """Create the admin main menu keyboard."""
        pause_text = "▶️ Resume" if is_paused else "⏸ Pause"
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔑 Keys", callback_data="admin_keys"),
                InlineKeyboardButton("📦 Stock", callback_data="admin_stock")
            ],
            [
                InlineKeyboardButton("⚡ Instant Delivery", callback_data="admin_instant"),
                InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
            ],
            [
                InlineKeyboardButton("📊 Analytics", callback_data="admin_analytics"),
                InlineKeyboardButton(pause_text, callback_data="admin_toggle_pause")
            ]
        ])
    
    @staticmethod
    def keys_menu() -> InlineKeyboardMarkup:
        """Create the keys management menu."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Generate Keys", callback_data="keys_generate"),
                InlineKeyboardButton("📋 List Keys", callback_data="keys_list")
            ],
            [
                InlineKeyboardButton("📊 Key Stats", callback_data="keys_stats")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_menu")]
        ])
    
    @staticmethod
    def stock_menu() -> InlineKeyboardMarkup:
        """Create the stock management menu."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Add Stock", callback_data="stock_add"),
                InlineKeyboardButton("📋 View Stock", callback_data="stock_view")
            ],
            [
                InlineKeyboardButton("📊 Stock Stats", callback_data="stock_stats"),
                InlineKeyboardButton("🗑 Clear Stock", callback_data="stock_clear")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_menu")]
        ])
    
    @staticmethod
    def balance_options(callback_prefix: str) -> InlineKeyboardMarkup:
        """Create balance selection keyboard."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("$50", callback_data=f"{callback_prefix}50"),
                InlineKeyboardButton("$100", callback_data=f"{callback_prefix}100"),
                InlineKeyboardButton("$150", callback_data=f"{callback_prefix}150")
            ],
            [
                InlineKeyboardButton("$200", callback_data=f"{callback_prefix}200"),
                InlineKeyboardButton("$250", callback_data=f"{callback_prefix}250"),
                InlineKeyboardButton("$300", callback_data=f"{callback_prefix}300")
            ],
            [
                InlineKeyboardButton("$350", callback_data=f"{callback_prefix}350"),
                InlineKeyboardButton("$400", callback_data=f"{callback_prefix}400")
            ],
            [InlineKeyboardButton("◀️ Cancel", callback_data="keys_menu")]
        ])
    
    @staticmethod
    def count_options(callback_prefix: str) -> InlineKeyboardMarkup:
        """Create count selection keyboard."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("1", callback_data=f"{callback_prefix}1"),
                InlineKeyboardButton("5", callback_data=f"{callback_prefix}5"),
                InlineKeyboardButton("10", callback_data=f"{callback_prefix}10")
            ],
            [
                InlineKeyboardButton("25", callback_data=f"{callback_prefix}25"),
                InlineKeyboardButton("50", callback_data=f"{callback_prefix}50"),
                InlineKeyboardButton("100", callback_data=f"{callback_prefix}100")
            ],
            [InlineKeyboardButton("◀️ Cancel", callback_data="keys_menu")]
        ])

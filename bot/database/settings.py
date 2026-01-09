"""
Bot settings stored in MongoDB.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .mongo import get_database
from bot.config import (
    DEFAULT_LOAD_PER_ROUND,
    DEFAULT_DELAY_PER_ROUND,
    DEFAULT_THREADS,
    DEFAULT_TARGET_BALANCE,
    DEFAULT_INSTANT_DELIVERY_RANGE_ENABLED,
    DEFAULT_INSTANT_DELIVERY_RANGE
)


# Default settings
DEFAULT_SETTINGS = {
    "_id": "global",
    "load_per_round": DEFAULT_LOAD_PER_ROUND,
    "delay_per_round": DEFAULT_DELAY_PER_ROUND,
    "threads": DEFAULT_THREADS,
    "default_target_balance": DEFAULT_TARGET_BALANCE,
    "proxy": "",
    "retry_same_card": True,
    "retry_halve_on_failure": False,
    "instant_delivery_range_enabled": DEFAULT_INSTANT_DELIVERY_RANGE_ENABLED,
    "instant_delivery_range": DEFAULT_INSTANT_DELIVERY_RANGE,
    "admin_ids": [],
    "paused": False,
    "updated_at": None
}


async def get_settings() -> Dict[str, Any]:
    """
    Get bot settings from database.
    
    Returns default settings if not found.
    """
    db = get_database()
    settings = await db.settings.find_one({"_id": "global"})
    
    if settings is None:
        # Initialize with defaults
        await db.settings.insert_one(DEFAULT_SETTINGS.copy())
        return DEFAULT_SETTINGS.copy()
    
    # Merge with defaults to ensure all keys exist
    merged = DEFAULT_SETTINGS.copy()
    merged.update(settings)
    return merged


async def update_settings(updates: Dict[str, Any]) -> bool:
    """
    Update bot settings.
    
    Args:
        updates: Dictionary of settings to update
        
    Returns:
        True if successful
    """
    db = get_database()
    updates["updated_at"] = datetime.now(timezone.utc)
    
    result = await db.settings.update_one(
        {"_id": "global"},
        {"$set": updates},
        upsert=True
    )
    
    return result.acknowledged


async def get_setting(key: str, default: Any = None) -> Any:
    """Get a single setting value."""
    settings = await get_settings()
    return settings.get(key, default)


async def set_setting(key: str, value: Any) -> bool:
    """Set a single setting value."""
    return await update_settings({key: value})

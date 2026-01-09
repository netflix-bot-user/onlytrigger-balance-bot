"""
Permission checks for bot commands.
"""
from bot.config import ADMIN_IDS


async def is_admin(user_id: int) -> bool:
    """
    Check if a user is an admin.
    
    Checks both config ADMIN_IDS and database settings.
    """
    # Check config first
    if user_id in ADMIN_IDS:
        return True
    
    # Check database settings (lazy import to avoid circular dependency)
    try:
        from bot.database.settings import get_settings
        settings = await get_settings()
        db_admins = settings.get("admin_ids", [])
        return user_id in db_admins
    except Exception:
        return False


async def add_admin(user_id: int) -> bool:
    """Add a user as admin in database."""
    from bot.database.settings import update_settings
    
    settings = await get_settings()
    admin_ids = settings.get("admin_ids", [])
    
    if user_id not in admin_ids:
        admin_ids.append(user_id)
        await update_settings({"admin_ids": admin_ids})
        return True
    return False


async def remove_admin(user_id: int) -> bool:
    """Remove a user from admin list in database."""
    from bot.database.settings import update_settings
    
    # Cannot remove config admins
    if user_id in ADMIN_IDS:
        return False
    
    settings = await get_settings()
    admin_ids = settings.get("admin_ids", [])
    
    if user_id in admin_ids:
        admin_ids.remove(user_id)
        await update_settings({"admin_ids": admin_ids})
        return True
    return False

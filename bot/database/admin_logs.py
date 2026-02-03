"""
Admin Logs collection operations.

Tracks all admin actions for audit trail and security.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId

from .mongo import get_database


class AdminAction:
    """Admin action types."""
    KEY_GENERATE = "key_generate"
    KEY_DELETE = "key_delete"
    KEY_REVOKE = "key_revoke"
    STOCK_ADD = "stock_add"
    STOCK_CLEAR = "stock_clear"
    STOCK_DELETE = "stock_delete"
    INSTANT_ADD = "instant_add"
    INSTANT_CLEAR = "instant_clear"
    INSTANT_DELETE = "instant_delete"
    SETTINGS_UPDATE = "settings_update"
    ADMIN_ADD = "admin_add"
    ADMIN_REMOVE = "admin_remove"
    USER_BAN = "user_ban"
    USER_UNBAN = "user_unban"
    SYSTEM_CONFIG = "system_config"


class AdminLogsDB:
    """Database operations for admin action logs."""
    
    @staticmethod
    def _collection():
        return get_database().admin_logs
    
    @classmethod
    async def log(
        cls,
        action: str,
        admin_id: int,
        admin_username: str = None,
        details: Dict[str, Any] = None,
        target_id: str = None,
        success: bool = True,
        error_message: str = None
    ) -> str:
        """
        Log an admin action.
        
        Args:
            action: Type of action (use AdminAction constants)
            admin_id: Telegram user ID of admin
            admin_username: Username of admin
            details: Additional details about the action
            target_id: ID of affected resource
            success: Whether action succeeded
            error_message: Error message if failed
            
        Returns:
            Inserted log ID
        """
        doc = {
            "action": action,
            "admin_id": admin_id,
            "admin_username": admin_username,
            "timestamp": datetime.now(timezone.utc),
            "details": details,
            "target_id": target_id,
            "success": success,
            "error_message": error_message
        }
        
        result = await cls._collection().insert_one(doc)
        return str(result.inserted_id)
    
    @classmethod
    async def get_logs(
        cls,
        action: Optional[str] = None,
        admin_id: Optional[int] = None,
        limit: int = 100,
        skip: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get admin logs with filtering.
        
        Args:
            action: Filter by action type
            admin_id: Filter by admin
            limit: Max results
            skip: Skip for pagination
            start_date: Filter from date
            end_date: Filter to date
        """
        query = {}
        
        if action:
            query["action"] = action
        if admin_id:
            query["admin_id"] = admin_id
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date
            if end_date:
                query["timestamp"]["$lte"] = end_date
        
        cursor = cls._collection().find(query).sort("timestamp", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @classmethod
    async def get_admin_activity(cls, admin_id: int, days: int = 7) -> Dict[str, Any]:
        """Get activity summary for an admin."""
        from datetime import timedelta
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "admin_id": admin_id,
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": "$action",
                    "count": {"$sum": 1},
                    "last_action": {"$max": "$timestamp"}
                }
            }
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=50)
        
        return {
            "admin_id": admin_id,
            "period_days": days,
            "actions": {r["_id"]: r["count"] for r in results},
            "total_actions": sum(r["count"] for r in results)
        }
    
    @classmethod
    async def get_recent_activity(cls, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most recent admin activity."""
        return await cls.get_logs(limit=limit)
    
    @classmethod
    async def count_by_action(cls, days: int = 30) -> Dict[str, int]:
        """Count actions by type in the last N days."""
        from datetime import timedelta
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {"_id": "$action", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=50)
        
        return {r["_id"]: r["count"] for r in results}

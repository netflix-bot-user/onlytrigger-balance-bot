"""
Users collection operations.

Tracks all users who interact with the bot.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId

from .mongo import get_database


class UsersDB:
    """Database operations for user tracking."""
    
    @staticmethod
    def _collection():
        return get_database().users
    
    @classmethod
    async def get_or_create(
        cls,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None
    ) -> Dict[str, Any]:
        """
        Get user or create if not exists.
        
        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            
        Returns:
            User document
        """
        now = datetime.now(timezone.utc)
        
        # Try to find and update
        result = await cls._collection().find_one_and_update(
            {"telegram_id": telegram_id},
            {
                "$set": {
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "last_active": now
                },
                "$setOnInsert": {
                    "telegram_id": telegram_id,
                    "created_at": now,
                    "is_banned": False,
                    "total_redemptions": 0,
                    "total_value_redeemed": 0
                }
            },
            upsert=True,
            return_document=True
        )
        
        return result
    
    @classmethod
    async def get_by_id(cls, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID."""
        return await cls._collection().find_one({"telegram_id": telegram_id})
    
    @classmethod
    async def update_redemption(
        cls,
        telegram_id: int,
        balance_value: float
    ) -> bool:
        """
        Update user's redemption stats.
        
        Args:
            telegram_id: User's Telegram ID
            balance_value: Value of redeemed balance
        """
        result = await cls._collection().update_one(
            {"telegram_id": telegram_id},
            {
                "$inc": {
                    "total_redemptions": 1,
                    "total_value_redeemed": balance_value
                },
                "$set": {"last_active": datetime.now(timezone.utc)}
            }
        )
        return result.modified_count > 0
    
    @classmethod
    async def ban_user(
        cls,
        telegram_id: int,
        banned_by: int,
        reason: str = None
    ) -> bool:
        """Ban a user."""
        result = await cls._collection().update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {
                    "is_banned": True,
                    "ban_reason": reason,
                    "banned_at": datetime.now(timezone.utc),
                    "banned_by": banned_by
                }
            }
        )
        return result.modified_count > 0
    
    @classmethod
    async def unban_user(cls, telegram_id: int) -> bool:
        """Unban a user."""
        result = await cls._collection().update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {"is_banned": False},
                "$unset": {"ban_reason": "", "banned_at": "", "banned_by": ""}
            }
        )
        return result.modified_count > 0
    
    @classmethod
    async def is_banned(cls, telegram_id: int) -> bool:
        """Check if user is banned."""
        user = await cls._collection().find_one(
            {"telegram_id": telegram_id},
            {"is_banned": 1}
        )
        return user.get("is_banned", False) if user else False
    
    @classmethod
    async def get_all(
        cls,
        banned_only: bool = False,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all users with optional filtering."""
        query = {}
        if banned_only:
            query["is_banned"] = True
        
        cursor = cls._collection().find(query).sort("last_active", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @classmethod
    async def count(cls, banned_only: bool = False) -> int:
        """Count users."""
        query = {"is_banned": True} if banned_only else {}
        return await cls._collection().count_documents(query)
    
    @classmethod
    async def get_top_users(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by redemption value."""
        cursor = cls._collection().find(
            {"total_redemptions": {"$gt": 0}}
        ).sort("total_value_redeemed", -1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    @classmethod
    async def get_stats(cls) -> Dict[str, Any]:
        """Get user statistics."""
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_users": {"$sum": 1},
                    "banned_users": {
                        "$sum": {"$cond": [{"$eq": ["$is_banned", True]}, 1, 0]}
                    },
                    "total_redemptions": {"$sum": "$total_redemptions"},
                    "total_value": {"$sum": "$total_value_redeemed"},
                    "users_with_redemptions": {
                        "$sum": {"$cond": [{"$gt": ["$total_redemptions", 0]}, 1, 0]}
                    }
                }
            }
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=1)
        
        if results:
            r = results[0]
            return {
                "total_users": r["total_users"],
                "banned_users": r["banned_users"],
                "active_users": r["total_users"] - r["banned_users"],
                "users_with_redemptions": r["users_with_redemptions"],
                "total_redemptions": r["total_redemptions"],
                "total_value_redeemed": r["total_value"]
            }
        
        return {
            "total_users": 0,
            "banned_users": 0,
            "active_users": 0,
            "users_with_redemptions": 0,
            "total_redemptions": 0,
            "total_value_redeemed": 0
        }
    
    @classmethod
    async def add_note(cls, telegram_id: int, note: str) -> bool:
        """Add admin note to user."""
        result = await cls._collection().update_one(
            {"telegram_id": telegram_id},
            {"$set": {"notes": note}}
        )
        return result.modified_count > 0

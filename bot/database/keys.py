"""
Keys collection operations.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId

from .mongo import get_database
from bot.utils.keygen import generate_key


class KeysDB:
    """Database operations for redemption keys."""
    
    @staticmethod
    def _collection():
        return get_database().keys
    
    @classmethod
    async def generate(
        cls,
        target_balance: int,
        count: int = 1,
        created_by: int = None
    ) -> List[str]:
        """
        Generate new redemption keys.
        
        Args:
            target_balance: Target balance for the key
            count: Number of keys to generate
            created_by: Telegram user ID of admin who created the key
            
        Returns:
            List of generated key strings
        """
        keys = []
        documents = []
        
        for _ in range(count):
            key = generate_key()
            keys.append(key)
            documents.append({
                "key": key,
                "target_balance": target_balance,
                "created_at": datetime.now(timezone.utc),
                "created_by": created_by,
                "status": "active",  # active, used, expired
                "used_by": None,
                "used_at": None,
                "delivered_account_id": None
            })
        
        await cls._collection().insert_many(documents)
        return keys
    
    @classmethod
    async def get_by_key(cls, key: str) -> Optional[Dict[str, Any]]:
        """Get a key document by its key string."""
        return await cls._collection().find_one({"key": key})
    
    @classmethod
    async def get_by_id(cls, key_id: str) -> Optional[Dict[str, Any]]:
        """Get a key document by its ObjectId."""
        return await cls._collection().find_one({"_id": ObjectId(key_id)})
    
    @classmethod
    async def claim_key(
        cls,
        key: str,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically claim a key for processing (prevents double redemption).
        
        Uses findOneAndUpdate to atomically check status AND update in one operation.
        This prevents race conditions where two requests could both pass the status check.
        
        Args:
            key: The key string
            user_id: Telegram user ID attempting to claim
            
        Returns:
            The key document if successfully claimed, None if already claimed/used
        """
        result = await cls._collection().find_one_and_update(
            {"key": key, "status": "active"},
            {
                "$set": {
                    "status": "processing",
                    "claimed_by": user_id,
                    "claimed_at": datetime.now(timezone.utc)
                }
            },
            return_document=True
        )
        return result
    
    @classmethod
    async def release_key(cls, key: str) -> bool:
        """
        Release a claimed key back to active status (for failed redemptions).
        
        Args:
            key: The key string
            
        Returns:
            True if successful
        """
        result = await cls._collection().update_one(
            {"key": key, "status": "processing"},
            {
                "$set": {
                    "status": "active",
                    "claimed_by": None,
                    "claimed_at": None
                }
            }
        )
        return result.modified_count > 0
    
    @classmethod
    async def use_key(
        cls,
        key: str,
        user_id: int,
        account_id: str
    ) -> bool:
        """
        Mark a key as used (after successful delivery).
        
        Args:
            key: The key string
            user_id: Telegram user ID who redeemed the key
            account_id: ID of the delivered account
            
        Returns:
            True if successful, False if key not found or not in processing state
        """
        result = await cls._collection().update_one(
            {"key": key, "status": {"$in": ["active", "processing"]}},
            {
                "$set": {
                    "status": "used",
                    "used_by": user_id,
                    "used_at": datetime.now(timezone.utc),
                    "delivered_account_id": account_id
                },
                "$unset": {
                    "claimed_by": "",
                    "claimed_at": ""
                }
            }
        )
        return result.modified_count > 0
    
    @classmethod
    async def delete(cls, key: str) -> bool:
        """Delete a key by its key string."""
        result = await cls._collection().delete_one({"key": key})
        return result.deleted_count > 0
    
    @classmethod
    async def delete_by_id(cls, key_id: str) -> bool:
        """Delete a key by its ObjectId."""
        result = await cls._collection().delete_one({"_id": ObjectId(key_id)})
        return result.deleted_count > 0
    
    @classmethod
    async def get_all(
        cls,
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all keys with optional filtering.
        
        Args:
            status: Filter by status (active, used, expired)
            limit: Maximum number of keys to return
            skip: Number of keys to skip (for pagination)
        """
        query = {}
        if status:
            query["status"] = status
        
        cursor = cls._collection().find(query).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @classmethod
    async def count(cls, status: Optional[str] = None) -> int:
        """Count keys with optional status filter."""
        query = {}
        if status:
            query["status"] = status
        return await cls._collection().count_documents(query)
    
    @classmethod
    async def count_by_balance(cls, target_balance: int, status: str = "active") -> int:
        """Count active keys for a specific target balance."""
        return await cls._collection().count_documents({
            "target_balance": target_balance,
            "status": status
        })
    
    @classmethod
    async def get_stats(cls) -> Dict[str, Any]:
        """Get key statistics."""
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=10)
        
        stats = {"active": 0, "used": 0, "expired": 0, "total": 0}
        for r in results:
            stats[r["_id"]] = r["count"]
            stats["total"] += r["count"]
        
        return stats
    
    @classmethod
    async def get_balance_distribution(cls, status: str = "active") -> Dict[int, int]:
        """Get count of keys by target balance."""
        pipeline = [
            {"$match": {"status": status}},
            {
                "$group": {
                    "_id": "$target_balance",
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=100)
        
        return {r["_id"]: r["count"] for r in results}
    
    @classmethod
    async def recover_stale_processing(cls, timeout_minutes: int = 10) -> List[Dict[str, Any]]:
        """
        Recover keys stuck in processing state (e.g., after bot restart).
        
        Keys that have been processing for longer than timeout are released back to active.
        
        Args:
            timeout_minutes: Minutes after which a processing key is considered stale
            
        Returns:
            List of recovered keys with user info for notification
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        
        # First, find all stale keys to get user info
        stale_keys = await cls._collection().find({
            "status": "processing",
            "claimed_at": {"$lt": cutoff_time}
        }).to_list(length=100)
        
        if not stale_keys:
            return []
        
        # Now update them
        await cls._collection().update_many(
            {
                "status": "processing",
                "claimed_at": {"$lt": cutoff_time}
            },
            {
                "$set": {
                    "status": "active",
                    "claimed_by": None,
                    "claimed_at": None
                }
            }
        )
        
        return stale_keys

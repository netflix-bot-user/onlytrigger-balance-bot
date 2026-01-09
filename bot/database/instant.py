"""
Instant Delivery collection operations.

Stores accounts that were partially loaded and can be delivered instantly
for matching target balances.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId

from .mongo import get_database
from .settings import get_settings


class InstantDeliveryDB:
    """Database operations for instant delivery accounts."""
    
    @staticmethod
    def _collection():
        return get_database().instant_delivery
    
    # Reasons for being in instant delivery
    REASON_PARTIAL_LOAD = "partial_load"      # Loading failed partway through
    REASON_PAUSED = "paused_loading"          # Stopped because another thread finished first
    REASON_MANUAL = "manual"                  # Manually added by admin
    
    @classmethod
    async def add(
        cls,
        credentials: str,
        balance: float,
        original_target: float,
        source: str = "partial_load",
        reason: str = None,
        resumable: bool = False,
        stock_account_id: str = None
    ) -> str:
        """
        Add an account to instant delivery.
        
        Args:
            credentials: Account credentials string
            balance: Actual loaded balance
            original_target: What the target was supposed to be
            source: How this account was added (partial_load, manual, paused_loading)
            reason: Detailed reason (partial_load, paused_loading, manual)
            resumable: Whether loading can be continued on this account
            stock_account_id: Reference to original stock account if resumable
            
        Returns:
            Inserted document ID as string
        """
        doc = {
            "credentials": credentials,
            "balance": balance,
            "original_target": original_target,
            "source": source,
            "reason": reason or source,
            "resumable": resumable,
            "stock_account_id": stock_account_id,
            "created_at": datetime.now(timezone.utc),
            "used": False,
            "used_by": None,
            "used_at": None,
            "key_used": None
        }
        
        result = await cls._collection().insert_one(doc)
        return str(result.inserted_id)
    
    @classmethod
    async def find_for_target(cls, target_balance: float) -> Optional[Dict[str, Any]]:
        """
        Find an available instant delivery account for a target balance.
        
        Matching logic:
        - If range disabled: exact match (balance == target)
        - If range enabled: target <= balance AND target >= (balance - range)
        - Never over: balance must be >= target
        
        Args:
            target_balance: The target balance to match
            
        Returns:
            Account document or None
        """
        settings = await get_settings()
        range_enabled = settings.get("instant_delivery_range_enabled", False)
        range_value = settings.get("instant_delivery_range", 50)
        
        if range_enabled:
            # Find account where: balance >= target AND balance <= target + range
            query = {
                "used": False,
                "balance": {
                    "$gte": target_balance,
                    "$lte": target_balance + range_value
                }
            }
        else:
            # Exact match only
            query = {
                "used": False,
                "balance": target_balance
            }
        
        # Get the best match (closest to target balance)
        cursor = cls._collection().find(query).sort("balance", 1).limit(1)
        results = await cursor.to_list(length=1)
        
        return results[0] if results else None
    
    @classmethod
    async def find_resumable_for_target(cls, target_balance: float) -> Optional[Dict[str, Any]]:
        """
        Find a resumable account that can be continued loading to reach target.
        
        Resumable accounts are those that were paused during parallel loading.
        We can continue loading them if target > current balance.
        
        Args:
            target_balance: The target balance to reach
            
        Returns:
            Account document or None (prioritizes highest existing balance)
        """
        # Find resumable accounts with balance < target (can still load more)
        query = {
            "used": False,
            "resumable": True,
            "balance": {"$lt": target_balance}
        }
        
        # Get the one with highest balance (less loading needed)
        cursor = cls._collection().find(query).sort("balance", -1).limit(1)
        results = await cursor.to_list(length=1)
        
        return results[0] if results else None
    
    @classmethod
    async def claim_for_resume(cls, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Atomically claim a resumable account for continued loading.
        
        Args:
            account_id: The instant delivery account ID
            
        Returns:
            Account document if claimed, None if already claimed/used
        """
        result = await cls._collection().find_one_and_update(
            {"_id": ObjectId(account_id), "used": False, "resumable": True},
            {
                "$set": {
                    "used": True,
                    "resuming": True,
                    "resume_started_at": datetime.now(timezone.utc)
                }
            },
            return_document=True
        )
        return result
    
    @classmethod
    async def update_after_resume(
        cls,
        account_id: str,
        new_balance: float,
        success: bool,
        new_target: float = None
    ) -> bool:
        """
        Update account after resume loading attempt.
        
        Args:
            account_id: The instant delivery account ID
            new_balance: Balance after loading attempt
            success: Whether target was reached
            new_target: The target that was attempted
        """
        if success:
            # Will be delivered, keep as used
            result = await cls._collection().update_one(
                {"_id": ObjectId(account_id)},
                {
                    "$set": {
                        "balance": new_balance,
                        "resuming": False,
                        "final_target": new_target
                    }
                }
            )
        else:
            # Failed to reach target, make available again
            result = await cls._collection().update_one(
                {"_id": ObjectId(account_id)},
                {
                    "$set": {
                        "balance": new_balance,
                        "used": False,
                        "resumable": new_balance > 0,
                        "resuming": False,
                        "original_target": new_target or 0
                    }
                }
            )
        return result.modified_count > 0
    
    @classmethod
    async def mark_used(
        cls,
        account_id: str,
        user_id: int,
        key_used: str = None
    ) -> bool:
        """
        Mark an instant delivery account as used.
        
        Args:
            account_id: Account document ID
            user_id: Telegram user ID who received the account
            key_used: The key that was redeemed
        """
        result = await cls._collection().update_one(
            {"_id": ObjectId(account_id), "used": False},
            {
                "$set": {
                    "used": True,
                    "used_by": user_id,
                    "used_at": datetime.now(timezone.utc),
                    "key_used": key_used
                }
            }
        )
        return result.modified_count > 0
    
    @classmethod
    async def get_by_id(cls, account_id: str) -> Optional[Dict[str, Any]]:
        """Get an instant delivery account by ID."""
        return await cls._collection().find_one({"_id": ObjectId(account_id)})
    
    @classmethod
    async def delete(cls, account_id: str) -> bool:
        """Delete an instant delivery account."""
        result = await cls._collection().delete_one({"_id": ObjectId(account_id)})
        return result.deleted_count > 0
    
    @classmethod
    async def get_all(
        cls,
        used: Optional[bool] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all instant delivery accounts with optional filtering."""
        query = {}
        if used is not None:
            query["used"] = used
        
        cursor = cls._collection().find(query).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @classmethod
    async def count(cls, used: Optional[bool] = None) -> int:
        """Count instant delivery accounts."""
        query = {}
        if used is not None:
            query["used"] = used
        return await cls._collection().count_documents(query)
    
    @classmethod
    async def get_balance_distribution(cls, used: bool = False) -> Dict[float, int]:
        """Get count of available accounts by balance."""
        pipeline = [
            {"$match": {"used": used}},
            {
                "$group": {
                    "_id": "$balance",
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=100)
        
        return {r["_id"]: r["count"] for r in results}
    
    @classmethod
    async def get_stats(cls) -> Dict[str, Any]:
        """Get instant delivery statistics."""
        available = await cls.count(used=False)
        used = await cls.count(used=True)
        distribution = await cls.get_balance_distribution(used=False)
        
        return {
            "available": available,
            "used": used,
            "total": available + used,
            "balance_distribution": distribution
        }
    
    @classmethod
    async def clear(cls, used_only: bool = False) -> int:
        """
        Clear instant delivery accounts.
        
        Args:
            used_only: If True, only clear used accounts
            
        Returns:
            Number of accounts deleted
        """
        query = {}
        if used_only:
            query["used"] = True
        
        result = await cls._collection().delete_many(query)
        return result.deleted_count

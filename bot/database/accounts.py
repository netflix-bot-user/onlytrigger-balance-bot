"""
Accounts (stock) collection operations.
AUTO-RECOVERY + REFUND SAFE VERSION
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from bson import ObjectId

from .mongo import get_database


class AccountsDB:
    """Database operations for account stock."""

    # ================== COLLECTION ==================

    @staticmethod
    def _collection():
        return get_database().accounts

    # ================== ADD ACCOUNTS ==================

    @classmethod
    async def add(cls, credentials: str, added_by: int = None) -> str:
        doc = {
            "credentials": credentials,
            "status": "available",
            "added_at": datetime.now(timezone.utc),
            "added_by": added_by,

            # delivery tracking
            "load_started_at": None,
            "load_finished_at": None,
            "initial_balance": None,
            "final_balance": None,
            "target_balance": None,
            "error_message": None
        }
        result = await cls._collection().insert_one(doc)
        return str(result.inserted_id)

    # ================== PICK ACCOUNT ==================

    @classmethod
    async def get_available(cls) -> Optional[Dict[str, Any]]:
        """
        Atomically pick ONE available account
        """
        return await cls._collection().find_one_and_update(
            {"status": "available"},
            {
                "$set": {
                    "status": "processing",
                    "load_started_at": datetime.now(timezone.utc)
                }
            },
            return_document=True
        )

    # ================== DELIVERY RESULT ==================

    @classmethod
    async def mark_loaded(
        cls,
        account_id: str,
        initial_balance: float,
        final_balance: float,
        target_balance: float
    ) -> bool:
        result = await cls._collection().update_one(
            {"_id": ObjectId(account_id)},
            {
                "$set": {
                    "status": "loaded",
                    "initial_balance": initial_balance,
                    "final_balance": final_balance,
                    "target_balance": target_balance,
                    "load_finished_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    @classmethod
    async def mark_failed(cls, account_id: str, error_message: str = None) -> bool:
        result = await cls._collection().update_one(
            {"_id": ObjectId(account_id)},
            {
                "$set": {
                    "status": "failed",
                    "error_message": error_message,
                    "load_finished_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    # ================== 🔥 AUTO RESTORE ==================

    @classmethod
    async def reset_to_available(cls) -> int:
        """
        Used when key is refunded.
        Moves ALL processing accounts back to available.
        """
        result = await cls._collection().update_many(
            {"status": "processing"},
            {
                "$set": {
                    "status": "available",
                    "load_started_at": None
                }
            }
        )
        return result.modified_count

    @classmethod
    async def recover_stale_processing(cls, timeout_minutes: int = 10) -> int:
        """
        Auto-recover accounts stuck in processing
        (server crash / bot restart / timeout)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

        result = await cls._collection().update_many(
            {
                "status": "processing",
                "load_started_at": {"$lt": cutoff}
            },
            {
                "$set": {
                    "status": "available",
                    "load_started_at": None
                }
            }
        )
        return result.modified_count

    @classmethod
    async def release_all_processing(cls) -> int:
        """
        Emergency admin release
        """
        result = await cls._collection().update_many(
            {"status": "processing"},
            {
                "$set": {
                    "status": "available",
                    "load_started_at": None
                }
            }
        )
        return result.modified_count

    # ================== 📊 STATS (FIXED) ==================

    @classmethod
    async def get_stats(cls) -> Dict[str, int]:
        """
        Used by admin menu
        """
        col = cls._collection()

        available = await col.count_documents({"status": "available"})
        processing = await col.count_documents({"status": "processing"})
        loaded = await col.count_documents({"status": "loaded"})
        failed = await col.count_documents({"status": "failed"})

        return {
            "available": available,
            "processing": processing,
            "loaded": loaded,
            "failed": failed,
            "total": available + processing + loaded + failed
        }

    @classmethod
    async def count(cls, status: Optional[str] = None) -> int:
        query = {}
        if status:
            query["status"] = status
        return await cls._collection().count_documents(query)

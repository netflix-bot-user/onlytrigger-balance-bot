"""
Accounts (stock) collection operations.
AUTO-RECOVERY ENABLED VERSION
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId

from .mongo import get_database


class AccountsDB:
    """Database operations for account stock."""

    @staticmethod
    def _collection():
        return get_database().accounts

    # -------------------- ADD ACCOUNTS --------------------

    @classmethod
    async def add(cls, credentials: str, added_by: int = None) -> str:
        doc = {
            "credentials": credentials,
            "status": "available",
            "added_at": datetime.now(timezone.utc),
            "added_by": added_by,
            "load_started_at": None,
            "load_finished_at": None,
            "initial_balance": None,
            "final_balance": None,
            "target_balance": None,
            "error_message": None
        }
        result = await cls._collection().insert_one(doc)
        return str(result.inserted_id)

    # -------------------- PICK ACCOUNTS --------------------

    @classmethod
    async def get_available(cls) -> Optional[Dict[str, Any]]:
        """Lock ONE account atomically"""
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

    # -------------------- DELIVERY RESULTS --------------------

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

    # -------------------- 🔥 AUTO RESTORE METHODS --------------------

    @classmethod
    async def reset_to_available(cls, account_ids: List[str]) -> int:
        """
        Used when key is refunded or delivery cancelled
        """
        result = await cls._collection().update_many(
            {
                "_id": {"$in": [ObjectId(aid) for aid in account_ids]},
                "status": "processing"
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
    async def recover_stale_processing(cls, timeout_minutes: int = 10) -> int:
        """
        Restore processing accounts stuck due to crash / timeout
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

    # -------------------- STATS --------------------

    @classmethod
    async def count(cls, status: Optional[str] = None) -> int:
        query = {}
        if status:
            query["status"] = status
        return await cls._collection().count_documents(query)

"""
Accounts (stock) collection operations.
AUTO-RECOVERY ENABLED VERSION
- processing is TEMPORARY
- auto release after delivery
- crash safe
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
            "load_duration_seconds": None,
            "initial_balance": None,
            "final_balance": None,
            "target_balance": None,
            "cards_used": None,
            "cards_total": None,
            "load_attempts": None,
            "error_message": None
        }

        result = await cls._collection().insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    async def add_bulk(cls, credentials_list: List[str], added_by: int = None) -> int:
        if not credentials_list:
            return 0

        now = datetime.now(timezone.utc)
        docs = []

        for creds in credentials_list:
            creds = creds.strip()
            if not creds:
                continue

            docs.append({
                "credentials": creds,
                "status": "available",
                "added_at": now,
                "added_by": added_by,
                "load_started_at": None,
                "load_finished_at": None,
                "load_duration_seconds": None,
                "initial_balance": None,
                "final_balance": None,
                "target_balance": None,
                "cards_used": None,
                "cards_total": None,
                "load_attempts": None,
                "error_message": None
            })

        if not docs:
            return 0

        result = await cls._collection().insert_many(docs)
        return len(result.inserted_ids)

    # -------------------- PICK ACCOUNTS --------------------

    @classmethod
    async def get_available(cls) -> Optional[Dict[str, Any]]:
        """
        Atomically lock ONE account.
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

    @classmethod
    async def get_multiple_available(cls, count: int) -> List[Dict[str, Any]]:
        accounts = []
        for _ in range(count):
            acc = await cls.get_available()
            if not acc:
                break
            accounts.append(acc)
        return accounts

    # -------------------- DELIVERY RESULT --------------------

    @classmethod
    async def mark_loaded(
        cls,
        account_id: str,
        initial_balance: float,
        final_balance: float,
        target_balance: float,
        cards_used: int = None,
        cards_total: int = None,
        load_attempts: int = None
    ) -> bool:
        """
        ACCOUNT USED SUCCESSFULLY → FINAL STATE
        """
        now = datetime.now(timezone.utc)

        result = await cls._collection().update_one(
            {"_id": ObjectId(account_id)},
            {
                "$set": {
                    "status": "loaded",
                    "load_finished_at": now,
                    "initial_balance": initial_balance,
                    "final_balance": final_balance,
                    "target_balance": target_balance,
                    "cards_used": cards_used,
                    "cards_total": cards_total,
                    "load_attempts": load_attempts
                }
            }
        )
        return result.modified_count > 0

    @classmethod
    async def mark_failed(
        cls,
        account_id: str,
        error_message: str = None
    ) -> bool:
        """
        FAILED = FINAL STATE
        """
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

    # -------------------- AUTO RESTORE / RECOVERY --------------------

    @classmethod
    async def recover_stale_processing(cls, timeout_minutes: int = 10) -> int:
        """
        Restore processing accounts stuck for more than timeout_minutes
        Called on bot startup
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

        result = await cls._collection().update_many(
            {
                "status": "processing",
                "load_started_at": {"$lt": cutoff_time}
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
    async def release_processing_accounts(cls) -> int:
        """
        Force release ALL processing accounts
        (used after delivery or admin reset)
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

    @classmethod
    async def get_stats(cls) -> Dict[str, Any]:
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=10)

        stats = {
            "available": 0,
            "processing": 0,
            "loaded": 0,
            "failed": 0,
            "total": 0
        }

        for r in results:
            if r["_id"] in stats:
                stats[r["_id"]] = r["count"]
            stats["total"] += r["count"]

        return stats

"""
Accounts (stock) collection operations.
FIXED VERSION:
- Failed accounts never return to available
- No infinite loop possible
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
            "status": "available",  # available, processing, loaded, failed
            "added_at": datetime.now(timezone.utc),
            "added_by": added_by,

            # analytics
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
        Atomically pick ONE available account and lock it as processing.
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

    # -------------------- RESULT HANDLING --------------------

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
        now = datetime.now(timezone.utc)

        acc = await cls._collection().find_one({"_id": ObjectId(account_id)})
        if not acc:
            return False

        duration = None
        if acc.get("load_started_at"):
            start = acc["load_started_at"]
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            duration = (now - start).total_seconds()

        result = await cls._collection().update_one(
            {"_id": ObjectId(account_id)},
            {
                "$set": {
                    "status": "loaded",
                    "load_finished_at": now,
                    "load_duration_seconds": duration,
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
        error_message: str = None,
        final_balance: float = None
    ) -> bool:
        """
        FAILED = FINAL STATE
        Never reused.
        """
        now = datetime.now(timezone.utc)

        acc = await cls._collection().find_one({"_id": ObjectId(account_id)})
        if not acc:
            return False

        duration = None
        if acc.get("load_started_at"):
            start = acc["load_started_at"]
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            duration = (now - start).total_seconds()

        result = await cls._collection().update_one(
            {"_id": ObjectId(account_id)},
            {
                "$set": {
                    "status": "failed",
                    "load_finished_at": now,
                    "load_duration_seconds": duration,
                    "error_message": error_message,
                    "final_balance": final_balance
                }
            }
        )
        return result.modified_count > 0

    # -------------------- DELETE (DELIVERED) --------------------

    @classmethod
    async def delete(cls, account_id: str) -> bool:
        """
        Used when account is DELIVERED to user.
        """
        result = await cls._collection().delete_one({"_id": ObjectId(account_id)})
        return result.deleted_count > 0

    # -------------------- RESET (DISABLED) --------------------

    @classmethod
    async def reset_to_available(cls, account_id: str) -> bool:
        """
        DISABLED ON PURPOSE.
        Failed or processed accounts must NEVER return to available.
        """
        return False

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

        stats = {"available": 0, "processing": 0, "loaded": 0, "failed": 0, "total": 0}
        for r in results:
            if r["_id"] in stats:
                stats[r["_id"]] = r["count"]
            stats["total"] += r["count"]

        return stats

    # -------------------- CLEANUP --------------------

    @classmethod
    async def clear_all(cls, status: Optional[str] = None) -> int:
        query = {}
        if status:
            query["status"] = status
        result = await cls._collection().delete_many(query)
        return result.deleted_count

    @classmethod
    async def recover_stale_processing(cls, timeout_minutes: int = 10) -> int:
        """
        If processing gets stuck → mark FAILED (NOT available)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

        result = await cls._collection().update_many(
            {
                "status": "processing",
                "load_started_at": {"$lt": cutoff}
            },
            {
                "$set": {
                    "status": "failed",
                    "error_message": "Processing timeout"
                }
            }
        )
        return result.modified_count

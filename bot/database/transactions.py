"""
Transactions collection operations.

E-commerce style transaction tracking for all redemptions.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId

from .mongo import get_database


class TransactionStatus:
    """Transaction status constants."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class TransactionType:
    """Transaction type constants."""
    REDEMPTION = "redemption"
    REFUND = "refund"
    MANUAL_DELIVERY = "manual_delivery"


class TransactionsDB:
    """Database operations for transaction tracking."""
    
    @staticmethod
    def _collection():
        return get_database().transactions
    
    @classmethod
    async def create(
        cls,
        user_id: int,
        key: str,
        target_balance: float,
        transaction_type: str = TransactionType.REDEMPTION
    ) -> str:
        """
        Create a new transaction.
        
        Args:
            user_id: Telegram user ID
            key: Redemption key
            target_balance: Target balance for the key
            transaction_type: Type of transaction
            
        Returns:
            Transaction ID
        """
        doc = {
            "type": transaction_type,
            "status": TransactionStatus.PENDING,
            "user_id": user_id,
            "key": key,
            "target_balance": target_balance,
            "actual_balance": None,
            "instant_delivery": False,
            "created_at": datetime.now(timezone.utc),
            "completed_at": None,
            "processing_time_seconds": None,
            "error_message": None
        }
        
        result = await cls._collection().insert_one(doc)
        return str(result.inserted_id)
    
    @classmethod
    async def start_processing(cls, transaction_id: str) -> bool:
        """Mark transaction as processing."""
        result = await cls._collection().update_one(
            {"_id": ObjectId(transaction_id)},
            {"$set": {"status": TransactionStatus.PROCESSING}}
        )
        return result.modified_count > 0
    
    @classmethod
    async def complete(
        cls,
        transaction_id: str,
        actual_balance: float,
        account_id: str = None,
        instant_delivery: bool = False
    ) -> bool:
        """
        Mark transaction as completed.
        
        Args:
            transaction_id: Transaction ID
            actual_balance: Actual balance delivered
            account_id: ID of delivered account
            instant_delivery: Whether instant delivery was used
        """
        now = datetime.now(timezone.utc)
        
        # Get transaction to calculate processing time
        txn = await cls._collection().find_one({"_id": ObjectId(transaction_id)})
        if not txn:
            return False
        
        processing_time = (now - txn["created_at"]).total_seconds()
        
        result = await cls._collection().update_one(
            {"_id": ObjectId(transaction_id)},
            {
                "$set": {
                    "status": TransactionStatus.COMPLETED,
                    "actual_balance": actual_balance,
                    "account_id": ObjectId(account_id) if account_id else None,
                    "instant_delivery": instant_delivery,
                    "completed_at": now,
                    "processing_time_seconds": processing_time
                }
            }
        )
        return result.modified_count > 0
    
    @classmethod
    async def fail(
        cls,
        transaction_id: str,
        error_message: str
    ) -> bool:
        """Mark transaction as failed."""
        now = datetime.now(timezone.utc)
        
        txn = await cls._collection().find_one({"_id": ObjectId(transaction_id)})
        if not txn:
            return False
        
        processing_time = (now - txn["created_at"]).total_seconds()
        
        result = await cls._collection().update_one(
            {"_id": ObjectId(transaction_id)},
            {
                "$set": {
                    "status": TransactionStatus.FAILED,
                    "error_message": error_message,
                    "completed_at": now,
                    "processing_time_seconds": processing_time
                }
            }
        )
        return result.modified_count > 0
    
    @classmethod
    async def refund(
        cls,
        transaction_id: str,
        refunded_by: int,
        reason: str = None
    ) -> bool:
        """Mark transaction as refunded."""
        result = await cls._collection().update_one(
            {"_id": ObjectId(transaction_id)},
            {
                "$set": {
                    "status": TransactionStatus.REFUNDED,
                    "refund_reason": reason,
                    "refunded_at": datetime.now(timezone.utc),
                    "refunded_by": refunded_by
                }
            }
        )
        return result.modified_count > 0
    
    @classmethod
    async def get_by_id(cls, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction by ID."""
        return await cls._collection().find_one({"_id": ObjectId(transaction_id)})
    
    @classmethod
    async def get_by_key(cls, key: str) -> Optional[Dict[str, Any]]:
        """Get transaction by key."""
        return await cls._collection().find_one({"key": key})
    
    @classmethod
    async def get_user_transactions(
        cls,
        user_id: int,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get transactions for a user."""
        cursor = cls._collection().find(
            {"user_id": user_id}
        ).sort("created_at", -1).skip(skip).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    @classmethod
    async def get_all(
        cls,
        status: Optional[str] = None,
        transaction_type: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all transactions with filtering."""
        query = {}
        if status:
            query["status"] = status
        if transaction_type:
            query["type"] = transaction_type
        
        cursor = cls._collection().find(query).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    @classmethod
    async def get_stats(cls) -> Dict[str, Any]:
        """Get transaction statistics."""
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1},
                    "total_value": {"$sum": "$actual_balance"},
                    "avg_processing_time": {"$avg": "$processing_time_seconds"}
                }
            }
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=10)
        
        stats = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "refunded": 0,
            "total": 0,
            "total_value_delivered": 0,
            "avg_processing_time": 0
        }
        
        total_time = 0
        time_count = 0
        
        for r in results:
            status = r["_id"]
            stats[status] = r["count"]
            stats["total"] += r["count"]
            
            if status == TransactionStatus.COMPLETED:
                stats["total_value_delivered"] = r["total_value"] or 0
                if r["avg_processing_time"]:
                    total_time += r["avg_processing_time"] * r["count"]
                    time_count += r["count"]
        
        if time_count > 0:
            stats["avg_processing_time"] = round(total_time / time_count, 2)
        
        return stats
    
    @classmethod
    async def get_daily_stats(cls, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily transaction statistics."""
        from datetime import timedelta
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        pipeline = [
            {"$match": {"created_at": {"$gte": start_date}}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                    },
                    "total": {"$sum": 1},
                    "completed": {
                        "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                    },
                    "failed": {
                        "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
                    },
                    "instant": {
                        "$sum": {"$cond": ["$instant_delivery", 1, 0]}
                    },
                    "total_value": {"$sum": "$actual_balance"},
                    "avg_time": {"$avg": "$processing_time_seconds"}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        return await cursor.to_list(length=days + 1)

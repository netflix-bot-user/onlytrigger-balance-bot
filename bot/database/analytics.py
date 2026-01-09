"""
Analytics collection operations.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from bson import ObjectId

from .mongo import get_database


class AnalyticsDB:
    """Database operations for analytics and metrics."""
    
    @staticmethod
    def _collection():
        return get_database().analytics
    
    @classmethod
    async def log_load(
        cls,
        account_id: str,
        success: bool,
        target_balance: float,
        final_balance: float,
        duration_seconds: float,
        partial: bool = False
    ):
        """
        Log a load operation for analytics.
        
        Args:
            account_id: The account that was loaded
            success: Whether the load was successful
            target_balance: Target balance requested
            final_balance: Actual final balance
            duration_seconds: How long the load took
            partial: Whether this was a partial load
        """
        doc = {
            "type": "load",
            "account_id": account_id,
            "success": success,
            "partial": partial,
            "target_balance": target_balance,
            "final_balance": final_balance,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now(timezone.utc),
            "date": datetime.now(timezone.utc).date().isoformat()
        }
        
        await cls._collection().insert_one(doc)
    
    @classmethod
    async def log_key_generated(cls, key: str, target_balance: float, admin_id: int):
        """Log key generation."""
        doc = {
            "type": "key_generated",
            "key": key,
            "target_balance": target_balance,
            "admin_id": admin_id,
            "timestamp": datetime.now(timezone.utc),
            "date": datetime.now(timezone.utc).date().isoformat()
        }
        await cls._collection().insert_one(doc)
    
    @classmethod
    async def log_key_redeemed(cls, key: str, user_id: int, instant: bool = False):
        """Log key redemption."""
        doc = {
            "type": "key_redeemed",
            "key": key,
            "user_id": user_id,
            "instant_delivery": instant,
            "timestamp": datetime.now(timezone.utc),
            "date": datetime.now(timezone.utc).date().isoformat()
        }
        await cls._collection().insert_one(doc)
    
    @classmethod
    async def get_daily_stats(cls, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily statistics for the last N days.
        
        Returns list of daily stats with loads, keys generated, keys redeemed.
        """
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        
        pipeline = [
            {"$match": {"date": {"$gte": start_date}}},
            {
                "$group": {
                    "_id": {
                        "date": "$date",
                        "type": "$type"
                    },
                    "count": {"$sum": 1},
                    "success_count": {
                        "$sum": {"$cond": [{"$eq": ["$success", True]}, 1, 0]}
                    },
                    "total_balance": {
                        "$sum": {"$ifNull": ["$final_balance", 0]}
                    },
                    "avg_duration": {
                        "$avg": {"$ifNull": ["$duration_seconds", 0]}
                    }
                }
            },
            {"$sort": {"_id.date": 1}}
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=100)
        
        # Reorganize by date
        daily_stats = {}
        for r in results:
            date = r["_id"]["date"]
            event_type = r["_id"]["type"]
            
            if date not in daily_stats:
                daily_stats[date] = {
                    "date": date,
                    "loads": 0,
                    "successful_loads": 0,
                    "failed_loads": 0,
                    "keys_generated": 0,
                    "keys_redeemed": 0,
                    "total_balance_loaded": 0,
                    "avg_load_duration": 0
                }
            
            if event_type == "load":
                daily_stats[date]["loads"] = r["count"]
                daily_stats[date]["successful_loads"] = r["success_count"]
                daily_stats[date]["failed_loads"] = r["count"] - r["success_count"]
                daily_stats[date]["total_balance_loaded"] = r["total_balance"]
                daily_stats[date]["avg_load_duration"] = round(r["avg_duration"], 2)
            elif event_type == "key_generated":
                daily_stats[date]["keys_generated"] = r["count"]
            elif event_type == "key_redeemed":
                daily_stats[date]["keys_redeemed"] = r["count"]
        
        return list(daily_stats.values())
    
    @classmethod
    async def get_overall_stats(cls) -> Dict[str, Any]:
        """Get overall statistics."""
        pipeline = [
            {
                "$facet": {
                    "loads": [
                        {"$match": {"type": "load"}},
                        {
                            "$group": {
                                "_id": None,
                                "total": {"$sum": 1},
                                "successful": {"$sum": {"$cond": [{"$eq": ["$success", True]}, 1, 0]}},
                                "partial": {"$sum": {"$cond": [{"$eq": ["$partial", True]}, 1, 0]}},
                                "total_balance": {"$sum": "$final_balance"},
                                "avg_duration": {"$avg": "$duration_seconds"}
                            }
                        }
                    ],
                    "keys_generated": [
                        {"$match": {"type": "key_generated"}},
                        {"$count": "count"}
                    ],
                    "keys_redeemed": [
                        {"$match": {"type": "key_redeemed"}},
                        {"$count": "count"}
                    ]
                }
            }
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=1)
        
        if not results:
            return {
                "total_loads": 0,
                "successful_loads": 0,
                "failed_loads": 0,
                "partial_loads": 0,
                "success_rate": 0,
                "total_balance_loaded": 0,
                "avg_load_duration": 0,
                "keys_generated": 0,
                "keys_redeemed": 0
            }
        
        r = results[0]
        
        loads = r["loads"][0] if r["loads"] else {}
        total_loads = loads.get("total", 0)
        successful = loads.get("successful", 0)
        
        return {
            "total_loads": total_loads,
            "successful_loads": successful,
            "failed_loads": total_loads - successful,
            "partial_loads": loads.get("partial", 0),
            "success_rate": round((successful / total_loads * 100) if total_loads > 0 else 0, 2),
            "total_balance_loaded": round(loads.get("total_balance", 0), 2),
            "avg_load_duration": round(loads.get("avg_duration", 0), 2),
            "keys_generated": r["keys_generated"][0]["count"] if r["keys_generated"] else 0,
            "keys_redeemed": r["keys_redeemed"][0]["count"] if r["keys_redeemed"] else 0
        }
    
    @classmethod
    async def get_load_time_distribution(cls) -> Dict[str, int]:
        """Get distribution of load times in buckets."""
        pipeline = [
            {"$match": {"type": "load", "duration_seconds": {"$exists": True}}},
            {
                "$bucket": {
                    "groupBy": "$duration_seconds",
                    "boundaries": [0, 60, 120, 300, 600, 1200, 3600],
                    "default": "3600+",
                    "output": {"count": {"$sum": 1}}
                }
            }
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=10)
        
        labels = {
            0: "0-1min",
            60: "1-2min",
            120: "2-5min",
            300: "5-10min",
            600: "10-20min",
            1200: "20-60min",
            "3600+": "60min+"
        }
        
        distribution = {}
        for r in results:
            label = labels.get(r["_id"], str(r["_id"]))
            distribution[label] = r["count"]
        
        return distribution

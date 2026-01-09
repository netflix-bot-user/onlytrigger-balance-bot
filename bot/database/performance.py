"""
Performance metrics collection operations.

Tracks system performance for monitoring and optimization.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId

from .mongo import get_database


class MetricType:
    """Metric type constants."""
    LOAD_TIME = "load_time"
    API_RESPONSE = "api_response"
    QUEUE_DEPTH = "queue_depth"
    SUCCESS_RATE = "success_rate"
    HOURLY_SUMMARY = "hourly_summary"
    DAILY_SUMMARY = "daily_summary"


class PerformanceDB:
    """Database operations for performance metrics."""
    
    @staticmethod
    def _collection():
        return get_database().performance
    
    @classmethod
    async def record_load_time(
        cls,
        duration_seconds: float,
        success: bool,
        account_id: str = None,
        target_balance: float = None
    ):
        """Record a load operation time."""
        doc = {
            "metric_type": MetricType.LOAD_TIME,
            "timestamp": datetime.now(timezone.utc),
            "value": duration_seconds,
            "unit": "seconds",
            "context": {
                "success": success,
                "account_id": account_id,
                "target_balance": target_balance
            }
        }
        await cls._collection().insert_one(doc)
    
    @classmethod
    async def record_api_response(
        cls,
        endpoint: str,
        response_time_ms: float,
        status_code: int = None,
        success: bool = True
    ):
        """Record an API response time."""
        doc = {
            "metric_type": MetricType.API_RESPONSE,
            "timestamp": datetime.now(timezone.utc),
            "value": response_time_ms,
            "unit": "milliseconds",
            "context": {
                "endpoint": endpoint,
                "status_code": status_code,
                "success": success
            }
        }
        await cls._collection().insert_one(doc)
    
    @classmethod
    async def record_queue_depth(cls, depth: int):
        """Record current queue depth."""
        doc = {
            "metric_type": MetricType.QUEUE_DEPTH,
            "timestamp": datetime.now(timezone.utc),
            "value": depth,
            "unit": "items"
        }
        await cls._collection().insert_one(doc)
    
    @classmethod
    async def get_load_time_stats(cls, hours: int = 24) -> Dict[str, Any]:
        """Get load time statistics for the last N hours."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        pipeline = [
            {
                "$match": {
                    "metric_type": MetricType.LOAD_TIME,
                    "timestamp": {"$gte": start_time}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "avg": {"$avg": "$value"},
                    "min": {"$min": "$value"},
                    "max": {"$max": "$value"},
                    "successful": {
                        "$sum": {"$cond": ["$context.success", 1, 0]}
                    }
                }
            }
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=1)
        
        if results:
            r = results[0]
            success_rate = (r["successful"] / r["count"] * 100) if r["count"] > 0 else 0
            return {
                "period_hours": hours,
                "total_loads": r["count"],
                "successful_loads": r["successful"],
                "success_rate": round(success_rate, 2),
                "avg_time_seconds": round(r["avg"] or 0, 2),
                "min_time_seconds": round(r["min"] or 0, 2),
                "max_time_seconds": round(r["max"] or 0, 2)
            }
        
        return {
            "period_hours": hours,
            "total_loads": 0,
            "successful_loads": 0,
            "success_rate": 0,
            "avg_time_seconds": 0,
            "min_time_seconds": 0,
            "max_time_seconds": 0
        }
    
    @classmethod
    async def get_percentiles(cls, hours: int = 24) -> Dict[str, float]:
        """Get load time percentiles."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Get all load times
        cursor = cls._collection().find(
            {
                "metric_type": MetricType.LOAD_TIME,
                "timestamp": {"$gte": start_time}
            },
            {"value": 1}
        ).sort("value", 1)
        
        values = [doc["value"] async for doc in cursor]
        
        if not values:
            return {"p50": 0, "p90": 0, "p95": 0, "p99": 0}
        
        def percentile(data, p):
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]
        
        return {
            "p50": round(percentile(values, 50), 2),
            "p90": round(percentile(values, 90), 2),
            "p95": round(percentile(values, 95), 2),
            "p99": round(percentile(values, 99), 2)
        }
    
    @classmethod
    async def get_hourly_breakdown(cls, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly breakdown of load times."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        pipeline = [
            {
                "$match": {
                    "metric_type": MetricType.LOAD_TIME,
                    "timestamp": {"$gte": start_time}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:00",
                            "date": "$timestamp"
                        }
                    },
                    "count": {"$sum": 1},
                    "avg_time": {"$avg": "$value"},
                    "successful": {
                        "$sum": {"$cond": ["$context.success", 1, 0]}
                    }
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=hours + 1)
        
        return [
            {
                "hour": r["_id"],
                "loads": r["count"],
                "successful": r["successful"],
                "avg_time": round(r["avg_time"], 2)
            }
            for r in results
        ]
    
    @classmethod
    async def generate_hourly_summary(cls):
        """Generate and store hourly summary."""
        now = datetime.now(timezone.utc)
        hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        hour_end = hour_start + timedelta(hours=1)
        
        pipeline = [
            {
                "$match": {
                    "metric_type": MetricType.LOAD_TIME,
                    "timestamp": {"$gte": hour_start, "$lt": hour_end}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "sum": {"$sum": "$value"},
                    "avg": {"$avg": "$value"},
                    "min": {"$min": "$value"},
                    "max": {"$max": "$value"},
                    "successful": {
                        "$sum": {"$cond": ["$context.success", 1, 0]}
                    }
                }
            }
        ]
        
        cursor = cls._collection().aggregate(pipeline)
        results = await cursor.to_list(length=1)
        
        if results:
            r = results[0]
            doc = {
                "metric_type": MetricType.HOURLY_SUMMARY,
                "timestamp": now,
                "period_start": hour_start,
                "period_end": hour_end,
                "aggregation": {
                    "count": r["count"],
                    "sum": r["sum"],
                    "avg": r["avg"],
                    "min": r["min"],
                    "max": r["max"],
                    "successful": r["successful"],
                    "success_rate": (r["successful"] / r["count"] * 100) if r["count"] > 0 else 0
                }
            }
            await cls._collection().insert_one(doc)
    
    @classmethod
    async def cleanup_old_metrics(cls, days: int = 30):
        """Delete metrics older than N days (keep summaries longer)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Delete raw metrics but keep summaries
        result = await cls._collection().delete_many({
            "metric_type": {"$in": [MetricType.LOAD_TIME, MetricType.API_RESPONSE, MetricType.QUEUE_DEPTH]},
            "timestamp": {"$lt": cutoff}
        })
        
        return result.deleted_count

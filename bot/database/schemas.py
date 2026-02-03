"""
MongoDB Schema Validation Definitions.

Defines JSON Schema validators for all collections to ensure data integrity.
"""

# Keys Collection Schema
KEYS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["key", "target_balance", "status", "created_at"],
        "properties": {
            "key": {
                "bsonType": "string",
                "description": "Unique redemption key string"
            },
            "target_balance": {
                "bsonType": "number",
                "minimum": 5,
                "maximum": 500,
                "description": "Target balance for this key"
            },
            "status": {
                "enum": ["active", "used", "expired", "revoked"],
                "description": "Current status of the key"
            },
            "created_at": {
                "bsonType": "date",
                "description": "When the key was created"
            },
            "created_by": {
                "bsonType": ["long", "int", "null"],
                "description": "Admin Telegram user ID who created the key"
            },
            "used_by": {
                "bsonType": ["long", "int", "null"],
                "description": "User Telegram ID who redeemed the key"
            },
            "used_at": {
                "bsonType": ["date", "null"],
                "description": "When the key was redeemed"
            },
            "delivered_account_id": {
                "bsonType": ["string", "null"],
                "description": "ID of the account delivered for this key"
            },
            "expires_at": {
                "bsonType": ["date", "null"],
                "description": "Optional expiration date"
            },
            "notes": {
                "bsonType": ["string", "null"],
                "description": "Admin notes about this key"
            }
        }
    }
}

# Accounts (Stock) Collection Schema
ACCOUNTS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["credentials", "status", "added_at"],
        "properties": {
            "credentials": {
                "bsonType": "string",
                "description": "Account credentials (sess:xbc:uid:ua)"
            },
            "status": {
                "enum": ["available", "processing", "loaded", "failed", "reserved", "delivered"],
                "description": "Current status of the account"
            },
            "added_at": {
                "bsonType": "date",
                "description": "When the account was added to stock"
            },
            "added_by": {
                "bsonType": ["long", "int", "null"],
                "description": "Admin who added this account"
            },
            "load_started_at": {
                "bsonType": ["date", "null"],
                "description": "When loading started"
            },
            "load_finished_at": {
                "bsonType": ["date", "null"],
                "description": "When loading finished"
            },
            "load_duration_seconds": {
                "bsonType": ["double", "int", "null"],
                "description": "Total loading duration in seconds"
            },
            "initial_balance": {
                "bsonType": ["double", "int", "null"],
                "description": "Balance before loading"
            },
            "final_balance": {
                "bsonType": ["double", "int", "null"],
                "description": "Balance after loading"
            },
            "target_balance": {
                "bsonType": ["double", "int", "null"],
                "description": "Target balance requested"
            },
            "cards_used": {
                "bsonType": ["int", "null"],
                "description": "Number of cards used for loading"
            },
            "cards_total": {
                "bsonType": ["int", "null"],
                "description": "Total cards available on account"
            },
            "load_attempts": {
                "bsonType": ["int", "null"],
                "description": "Number of payment attempts made"
            },
            "error_message": {
                "bsonType": ["string", "null"],
                "description": "Error message if loading failed"
            },
            "delivered_to": {
                "bsonType": ["long", "int", "null"],
                "description": "User ID who received this account"
            },
            "delivered_at": {
                "bsonType": ["date", "null"],
                "description": "When the account was delivered"
            },
            "key_used": {
                "bsonType": ["string", "null"],
                "description": "Key that was used to redeem this account"
            }
        }
    }
}

# Instant Delivery Collection Schema
INSTANT_DELIVERY_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["credentials", "balance", "used", "created_at"],
        "properties": {
            "credentials": {
                "bsonType": "string",
                "description": "Account credentials"
            },
            "balance": {
                "bsonType": "number",
                "minimum": 0,
                "description": "Actual loaded balance"
            },
            "original_target": {
                "bsonType": ["number", "null"],
                "description": "Original target balance that was requested"
            },
            "source": {
                "enum": ["partial_load", "manual", "preloaded"],
                "description": "How this account was added"
            },
            "created_at": {
                "bsonType": "date",
                "description": "When added to instant delivery"
            },
            "used": {
                "bsonType": "bool",
                "description": "Whether this account has been delivered"
            },
            "used_by": {
                "bsonType": ["long", "int", "null"],
                "description": "User ID who received this account"
            },
            "used_at": {
                "bsonType": ["date", "null"],
                "description": "When the account was delivered"
            },
            "key_used": {
                "bsonType": ["string", "null"],
                "description": "Key used to redeem this account"
            }
        }
    }
}

# Admin Logs Collection Schema
ADMIN_LOGS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["action", "admin_id", "timestamp"],
        "properties": {
            "action": {
                "enum": [
                    "key_generate", "key_delete", "key_revoke",
                    "stock_add", "stock_clear", "stock_delete",
                    "instant_add", "instant_clear", "instant_delete",
                    "settings_update", "admin_add", "admin_remove",
                    "user_ban", "user_unban", "system_config"
                ],
                "description": "Type of admin action"
            },
            "admin_id": {
                "bsonType": ["long", "int"],
                "description": "Telegram user ID of admin"
            },
            "admin_username": {
                "bsonType": ["string", "null"],
                "description": "Username of admin at time of action"
            },
            "timestamp": {
                "bsonType": "date",
                "description": "When the action occurred"
            },
            "details": {
                "bsonType": ["object", "null"],
                "description": "Additional details about the action"
            },
            "target_id": {
                "bsonType": ["string", "null"],
                "description": "ID of the affected resource"
            },
            "ip_address": {
                "bsonType": ["string", "null"],
                "description": "IP address if available"
            },
            "success": {
                "bsonType": "bool",
                "description": "Whether the action succeeded"
            },
            "error_message": {
                "bsonType": ["string", "null"],
                "description": "Error message if action failed"
            }
        }
    }
}

# Users Collection Schema (for tracking users)
USERS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["telegram_id", "created_at"],
        "properties": {
            "telegram_id": {
                "bsonType": ["long", "int"],
                "description": "Telegram user ID"
            },
            "username": {
                "bsonType": ["string", "null"],
                "description": "Telegram username"
            },
            "first_name": {
                "bsonType": ["string", "null"],
                "description": "User's first name"
            },
            "last_name": {
                "bsonType": ["string", "null"],
                "description": "User's last name"
            },
            "created_at": {
                "bsonType": "date",
                "description": "First interaction with bot"
            },
            "last_active": {
                "bsonType": ["date", "null"],
                "description": "Last interaction with bot"
            },
            "is_banned": {
                "bsonType": "bool",
                "description": "Whether user is banned"
            },
            "ban_reason": {
                "bsonType": ["string", "null"],
                "description": "Reason for ban"
            },
            "banned_at": {
                "bsonType": ["date", "null"],
                "description": "When user was banned"
            },
            "banned_by": {
                "bsonType": ["long", "int", "null"],
                "description": "Admin who banned the user"
            },
            "total_redemptions": {
                "bsonType": "int",
                "description": "Total keys redeemed by user"
            },
            "total_value_redeemed": {
                "bsonType": "number",
                "description": "Total balance value redeemed"
            },
            "notes": {
                "bsonType": ["string", "null"],
                "description": "Admin notes about user"
            }
        }
    }
}

# Transactions Collection Schema (e-commerce tracking)
TRANSACTIONS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["type", "status", "created_at"],
        "properties": {
            "type": {
                "enum": ["redemption", "refund", "manual_delivery"],
                "description": "Type of transaction"
            },
            "status": {
                "enum": ["pending", "processing", "completed", "failed", "refunded"],
                "description": "Transaction status"
            },
            "user_id": {
                "bsonType": ["long", "int"],
                "description": "User who initiated transaction"
            },
            "key": {
                "bsonType": ["string", "null"],
                "description": "Key used in transaction"
            },
            "key_id": {
                "bsonType": ["objectId", "null"],
                "description": "Reference to key document"
            },
            "account_id": {
                "bsonType": ["objectId", "null"],
                "description": "Reference to account document"
            },
            "target_balance": {
                "bsonType": ["number", "null"],
                "description": "Target balance requested"
            },
            "actual_balance": {
                "bsonType": ["number", "null"],
                "description": "Actual balance delivered"
            },
            "instant_delivery": {
                "bsonType": "bool",
                "description": "Whether instant delivery was used"
            },
            "created_at": {
                "bsonType": "date",
                "description": "When transaction started"
            },
            "completed_at": {
                "bsonType": ["date", "null"],
                "description": "When transaction completed"
            },
            "processing_time_seconds": {
                "bsonType": ["double", "int", "null"],
                "description": "Total processing time"
            },
            "error_message": {
                "bsonType": ["string", "null"],
                "description": "Error if transaction failed"
            },
            "refund_reason": {
                "bsonType": ["string", "null"],
                "description": "Reason for refund if applicable"
            },
            "refunded_at": {
                "bsonType": ["date", "null"],
                "description": "When refund was processed"
            },
            "refunded_by": {
                "bsonType": ["long", "int", "null"],
                "description": "Admin who processed refund"
            }
        }
    }
}

# Performance Metrics Collection Schema
PERFORMANCE_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["metric_type", "timestamp"],
        "properties": {
            "metric_type": {
                "enum": ["load_time", "api_response", "queue_depth", "success_rate", "hourly_summary", "daily_summary"],
                "description": "Type of metric"
            },
            "timestamp": {
                "bsonType": "date",
                "description": "When metric was recorded"
            },
            "value": {
                "bsonType": "number",
                "description": "Metric value"
            },
            "unit": {
                "bsonType": ["string", "null"],
                "description": "Unit of measurement"
            },
            "context": {
                "bsonType": ["object", "null"],
                "description": "Additional context"
            },
            "period_start": {
                "bsonType": ["date", "null"],
                "description": "Start of aggregation period"
            },
            "period_end": {
                "bsonType": ["date", "null"],
                "description": "End of aggregation period"
            },
            "aggregation": {
                "bsonType": ["object", "null"],
                "description": "Aggregated statistics",
                "properties": {
                    "count": {"bsonType": "int"},
                    "sum": {"bsonType": "number"},
                    "avg": {"bsonType": "number"},
                    "min": {"bsonType": "number"},
                    "max": {"bsonType": "number"},
                    "p50": {"bsonType": "number"},
                    "p95": {"bsonType": "number"},
                    "p99": {"bsonType": "number"}
                }
            }
        }
    }
}

# Settings Collection Schema
SETTINGS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["_id"],
        "properties": {
            "_id": {
                "bsonType": "string",
                "description": "Settings document ID (global)"
            },
            "load_per_round": {
                "bsonType": "int",
                "minimum": 5,
                "maximum": 100,
                "description": "Amount to load per payment round"
            },
            "delay_per_round": {
                "bsonType": "int",
                "minimum": 60,
                "maximum": 600,
                "description": "Delay between payment rounds in seconds"
            },
            "threads": {
                "bsonType": "int",
                "minimum": 1,
                "maximum": 50,
                "description": "Number of concurrent loading threads"
            },
            "proxy": {
                "bsonType": ["string", "null"],
                "description": "HTTP proxy URL"
            },
            "retry_same_card": {
                "bsonType": "bool",
                "description": "Whether to retry failed payments on same card"
            },
            "retry_halve_on_failure": {
                "bsonType": "bool",
                "description": "Whether to halve amount on payment failure"
            },
            "instant_delivery_range_enabled": {
                "bsonType": "bool",
                "description": "Whether to allow range matching for instant delivery"
            },
            "instant_delivery_range": {
                "bsonType": "int",
                "minimum": 0,
                "maximum": 100,
                "description": "Range for instant delivery matching"
            },
            "admin_ids": {
                "bsonType": "array",
                "items": {"bsonType": ["long", "int"]},
                "description": "List of admin Telegram user IDs"
            },
            "maintenance_mode": {
                "bsonType": "bool",
                "description": "Whether bot is in maintenance mode"
            },
            "maintenance_message": {
                "bsonType": ["string", "null"],
                "description": "Message to show during maintenance"
            },
            "updated_at": {
                "bsonType": ["date", "null"],
                "description": "Last settings update time"
            },
            "updated_by": {
                "bsonType": ["long", "int", "null"],
                "description": "Admin who last updated settings"
            }
        }
    }
}


# Collection configurations with schemas and indexes
COLLECTIONS_CONFIG = {
    "keys": {
        "schema": KEYS_SCHEMA,
        "indexes": [
            {"keys": [("key", 1)], "unique": True},
            {"keys": [("status", 1)]},
            {"keys": [("target_balance", 1)]},
            {"keys": [("created_at", -1)]},
            {"keys": [("created_by", 1)]},
            {"keys": [("used_by", 1)]},
            {"keys": [("expires_at", 1)], "expireAfterSeconds": 0, "sparse": True}
        ]
    },
    "accounts": {
        "schema": ACCOUNTS_SCHEMA,
        "indexes": [
            {"keys": [("status", 1)]},
            {"keys": [("added_at", -1)]},
            {"keys": [("added_by", 1)]},
            {"keys": [("final_balance", 1)]},
            {"keys": [("load_duration_seconds", 1)]},
            {"keys": [("status", 1), ("added_at", -1)]}
        ]
    },
    "instant_delivery": {
        "schema": INSTANT_DELIVERY_SCHEMA,
        "indexes": [
            {"keys": [("balance", 1)]},
            {"keys": [("used", 1)]},
            {"keys": [("balance", 1), ("used", 1)]},
            {"keys": [("created_at", -1)]}
        ]
    },
    "admin_logs": {
        "schema": ADMIN_LOGS_SCHEMA,
        "indexes": [
            {"keys": [("action", 1)]},
            {"keys": [("admin_id", 1)]},
            {"keys": [("timestamp", -1)]},
            {"keys": [("action", 1), ("timestamp", -1)]}
        ]
    },
    "users": {
        "schema": USERS_SCHEMA,
        "indexes": [
            {"keys": [("telegram_id", 1)], "unique": True},
            {"keys": [("username", 1)], "sparse": True},
            {"keys": [("is_banned", 1)]},
            {"keys": [("last_active", -1)]},
            {"keys": [("total_redemptions", -1)]}
        ]
    },
    "transactions": {
        "schema": TRANSACTIONS_SCHEMA,
        "indexes": [
            {"keys": [("type", 1)]},
            {"keys": [("status", 1)]},
            {"keys": [("user_id", 1)]},
            {"keys": [("created_at", -1)]},
            {"keys": [("key", 1)], "sparse": True},
            {"keys": [("user_id", 1), ("created_at", -1)]}
        ]
    },
    "performance": {
        "schema": PERFORMANCE_SCHEMA,
        "indexes": [
            {"keys": [("metric_type", 1)]},
            {"keys": [("timestamp", -1)]},
            {"keys": [("metric_type", 1), ("timestamp", -1)]}
        ]
    },
    "settings": {
        "schema": SETTINGS_SCHEMA,
        "indexes": []
    },
    "analytics": {
        "schema": None,  # Flexible schema for analytics
        "indexes": [
            {"keys": [("type", 1)]},
            {"keys": [("date", 1)]},
            {"keys": [("timestamp", -1)]}
        ]
    }
}

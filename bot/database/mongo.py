"""
MongoDB connection management with schema validation.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import CollectionInvalid, OperationFailure
from typing import Optional
import logging

from bot.config import MONGO_URI, MONGO_DB_NAME
from .schemas import COLLECTIONS_CONFIG

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_db() -> AsyncIOMotorDatabase:
    """Connect to MongoDB and return the database instance."""
    global _client, _database
    
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
        _database = _client[MONGO_DB_NAME]
        
        # Setup collections with schema validation
        await _setup_collections()
        
        logger.info(f"✓ Connected to MongoDB: {MONGO_DB_NAME}")
    
    return _database


async def _setup_collections():
    """Setup collections with schema validation and indexes."""
    global _database
    
    for collection_name, config in COLLECTIONS_CONFIG.items():
        try:
            # Try to create collection with schema validation
            if config.get("schema"):
                try:
                    await _database.create_collection(
                        collection_name,
                        validator=config["schema"],
                        validationLevel="moderate",  # Allows updates to invalid docs
                        validationAction="warn"  # Log warnings instead of rejecting
                    )
                    logger.info(f"  ✓ Created collection: {collection_name}")
                except CollectionInvalid:
                    # Collection exists, update schema
                    await _database.command({
                        "collMod": collection_name,
                        "validator": config["schema"],
                        "validationLevel": "moderate",
                        "validationAction": "warn"
                    })
                    logger.info(f"  ✓ Updated schema: {collection_name}")
            
            # Create indexes
            for index_config in config.get("indexes", []):
                keys = index_config.pop("keys")
                try:
                    await _database[collection_name].create_index(keys, **index_config)
                except OperationFailure as e:
                    logger.warning(f"  ⚠ Index warning for {collection_name}: {e}")
                finally:
                    index_config["keys"] = keys  # Restore for next run
                    
        except Exception as e:
            logger.error(f"  ✗ Error setting up {collection_name}: {e}")


def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance. Must call connect_db first."""
    if _database is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _database


async def close_db():
    """Close the database connection."""
    global _client, _database
    
    if _client:
        _client.close()
        _client = None
        _database = None
        print("✓ MongoDB connection closed")

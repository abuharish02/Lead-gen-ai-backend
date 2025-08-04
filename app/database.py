# backend/app/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database = None

# Global database instance
db_instance = Database()

async def init_db():
    """Initialize database connection"""
    await connect_to_mongo()

async def connect_to_mongo():
    """Create database connection"""
    try:
        db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL)
        db_instance.database = db_instance.client[settings.DATABASE_NAME]
        
        # Test connection
        await db_instance.client.admin.command('ping')
        print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {str(e)}")
        logger.error(f"MongoDB connection failed: {str(e)}")
        raise

async def close_mongo_connection():
    """Close database connection"""
    if db_instance.client:
        db_instance.client.close()
        print("✅ MongoDB connection closed")

def get_database():
    """Get database instance"""
    return db_instance.database

def get_db():
    """Get database instance for API dependency"""
    return db_instance.database

# Sync version for scripts
def get_sync_database():
    """Get synchronous database connection for scripts"""
    client = MongoClient(settings.MONGODB_URL)
    return client[settings.DATABASE_NAME]

# Collection names
COLLECTIONS = {
    "companies": "companies",
    "analyses": "analyses", 
    "users": "users"
}
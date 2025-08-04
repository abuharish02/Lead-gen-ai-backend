"""Database initialization script with proper imports"""
import sys
import os
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import Base, engine
from app.models.analysis import Analysis
from app.models.company import Company  
from app.models.user import User
from app.config import settings

def initialize_database():
    """Initialize database with all tables"""
    try:
        print("🔧 Initializing database...")
        print(f"📍 Database URL: {settings.DATABASE_URL}")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database tables created successfully!")
        print("📋 Tables created:")
        for table in Base.metadata.tables.keys():
            print(f"   • {table}")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        raise

if __name__ == "__main__":
    initialize_database()
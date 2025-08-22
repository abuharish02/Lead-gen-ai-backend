"""Development server runner for Website Analyzer"""
import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("🚀 Starting Website Analyzer API Server...")
    print(f"📍 Environment: {'Development' if settings.DEBUG else 'Production'}")
    print(f"🔧 Database: {settings.MONGODB_URL}")
    print(f"🧠 Knowledge Base: {settings.KNOWLEDGE_BASE_DIR}")
    print(f"🤖 Gemini Model: {settings.GEMINI_MODEL}")
    print("-" * 50)
    
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )

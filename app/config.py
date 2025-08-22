from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # MongoDB Configuration
    MONGODB_URL: str
    DATABASE_NAME: str = "website_analyzer"
    
    # Gemini API
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Application
    SECRET_KEY: str
    DEBUG: bool = False
    ADMIN_EMAIL: str = "theanandsingh76@gmail.com"
    
    # CORS - Fixed Vercel URLs (removed trailing slash and duplicate)
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",  # Vite dev server
        "https://lead-gen-ai-frontend.vercel.app",  # Fixed: removed trailing slash
        "https://lead-gen-ai-frontend-595294038624.asia-south2.run.app",
        # Add additional Vercel preview URLs if needed
        # "https://lead-gen-ai-frontend-git-main-yourusername.vercel.app",
        # "https://lead-gen-ai-frontend-123abc.vercel.app",  # Preview deployments
    ]
    
    # File Upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "data/uploads"
    
    # RAG Settings
    KNOWLEDGE_BASE_DIR: str = "data/knowledge_base"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Server Configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8080
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
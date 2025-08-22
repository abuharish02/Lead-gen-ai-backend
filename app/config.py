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
    
    # CORS - Production GCP URLs only
    ALLOWED_ORIGINS: List[str] = [
        "https://lead-gen.nextinvision.com",  # Custom domain
        "https://lead-gen-ai-frontend-595294038624.asia-southeast1.run.app",  # Cloud Run frontend
        "https://lead-gen-ai-frontend-595294038624.asia-south2.run.app",  # Alternative Cloud Run URL
    ]
    
    # File Upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "data/uploads"
    
    # RAG Settings
    KNOWLEDGE_BASE_DIR: str = "data/knowledge_base"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Server Configuration - Production GCP
    HOST: str = "0.0.0.0"  # Allow external connections
    PORT: int = 8080  # Cloud Run standard port
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
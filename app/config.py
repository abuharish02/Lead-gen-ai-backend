from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import field_validator
import os

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
    
    # CORS - This will now properly parse from environment variable
    ALLOWED_ORIGINS: Optional[List[str]] = None
    
    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse ALLOWED_ORIGINS from comma-separated string or list"""
        if v is None:
            return [
                "https://lead-gen.nextinvision.com",
                "https://lead-gen-ai-frontend-595294038624.asia-southeast1.run.app", 
                "https://lead-gen-ai-frontend-595294038624.asia-south2.run.app",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        if isinstance(v, str):
            # Handle comma-separated string from environment variable
            if v.strip() == "":
                return [
                    "https://lead-gen.nextinvision.com",
                    "https://lead-gen-ai-frontend-595294038624.asia-southeast1.run.app", 
                    "https://lead-gen-ai-frontend-595294038624.asia-south2.run.app",
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                ]
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        elif isinstance(v, list):
            return v
        return v
    
    # File Upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "data/uploads"
    
    # RAG Settings
    KNOWLEDGE_BASE_DIR: str = "data/knowledge_base"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Server Configuration - FIXED: Properly handle Cloud Run PORT
    HOST: str = "0.0.0.0"
    
    @property
    def PORT(self) -> int:
        """Get PORT from environment variable (Cloud Run) or default to 8000"""
        return int(os.environ.get("PORT", 8000))
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()
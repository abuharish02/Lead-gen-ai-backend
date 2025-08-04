# backend/app/main.py - FIXED VERSION
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
from app.api import analyze, bulk, reports, health
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print("🚀 Initializing database connection...")
    await connect_to_mongo()
    yield
    # Shutdown
    print("🔄 Closing database connection...")
    await close_mongo_connection()

app = FastAPI(
    title="AI Website Analysis Agent", 
    version="1.0.0",
    lifespan=lifespan
)

# Simplified but comprehensive CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Request logging middleware for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request details
    print(f"🔍 {request.method} {request.url}")
    print(f"🌐 Origin: {request.headers.get('origin', 'No origin')}")
    print(f"📋 Headers: {dict(request.headers)}")
    
    response = await call_next(request)
    
    # Log response details
    process_time = time.time() - start_time
    print(f"✅ Response: {response.status_code} in {process_time:.4f}s")
    print("-" * 50)
    
    return response

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(analyze.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(bulk.router, prefix="/api/v1", tags=["Bulk Processing"])
app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])

@app.get("/")
async def root():
    return {
        "message": "AI Website Analysis Agent",
        "version": "1.0.0",
        "status": "running",
        "cors_origins": "all_allowed"
    }

# Add a manual OPTIONS handler as a fallback
@app.options("/{full_path:path}")
async def options_handler(request: Request):
    """Handle all OPTIONS requests manually"""
    return {
        "message": "OPTIONS request handled",
        "path": str(request.url.path),
        "method": "OPTIONS"
    }
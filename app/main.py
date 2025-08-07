"""Main FastAPI application for Website Analyzer"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import traceback
import logging
import sys

# Import your API routers - EXACTLY as they are in your project
from app.api import analyze, reports, health, bulk
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, init_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    try:
        logger.info("🚀 Starting Website Analyzer API...")
        logger.info(f"📍 Environment: {'Development' if settings.DEBUG else 'Production'}")
        logger.info(f"🔧 Database: {settings.MONGODB_URL}")
        
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        traceback.print_exc()
        # Don't raise in production - let app start anyway for debugging
        yield
    finally:
        logger.info("🔄 Shutting down...")
        try:
            await close_mongo_connection()
            logger.info("✅ Database connection closed")
        except Exception as e:
            logger.error(f"⚠️ Error closing database: {e}")

# Create FastAPI app
app = FastAPI(
    title="AI Website Analysis Agent",
    description="AI-powered website analysis and lead generation tool",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration - Allow all for debugging
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Enhanced request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request details
    logger.info(f"🔍 {request.method} {request.url.path}")
    logger.info(f"🌐 Origin: {request.headers.get('origin', 'No origin')}")
    logger.info(f"🔑 User-Agent: {request.headers.get('user-agent', 'Unknown')}")
    
    if request.query_params:
        logger.info(f"📋 Query params: {dict(request.query_params)}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        if response.status_code >= 400:
            logger.error(f"❌ {request.method} {request.url.path} -> {response.status_code} ({process_time:.3f}s)")
        else:
            logger.info(f"✅ {request.method} {request.url.path} -> {response.status_code} ({process_time:.3f}s)")
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"💥 {request.method} {request.url.path} -> ERROR ({process_time:.3f}s): {str(e)}")
        logger.error(traceback.format_exc())
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Internal server error: {str(e)}",
                "path": str(request.url.path),
                "method": request.method
            }
        )

# Include routers with correct prefixes - THIS IS CRITICAL
try:
    logger.info("📡 Registering API routers...")
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(analyze.router, prefix="/api/v1", tags=["Analysis"]) 
    app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
    app.include_router(bulk.router, prefix="/api/v1", tags=["Bulk Processing"])
    logger.info("✅ All routers registered successfully")
    
except Exception as e:
    logger.error(f"❌ Error registering routers: {e}")
    traceback.print_exc()

# Root endpoint with comprehensive info
@app.get("/")
async def root():
    try:
        return {
            "message": "AI Website Analysis Agent",
            "version": "1.0.0",
            "status": "running",
            "environment": "production",
            "endpoints": {
                "docs": "/docs",
                "health": "/api/v1/health",
                "analyze_single": "POST /api/v1/analyze",
                "list_analyses": "GET /api/v1/analyze",
                "get_analysis": "GET /api/v1/analyze/{id}",
                "reports": "GET /api/v1/reports", 
                "report_stats": "GET /api/v1/reports/stats",
                "bulk_urls": "POST /api/v1/bulk/urls",
                "bulk_upload": "POST /api/v1/bulk/upload",
                "bulk_status": "GET /api/v1/bulk/{id}/status"
            },
            "cors": "enabled_for_all_origins",
            "database": "connected" if hasattr(app.state, 'db') else "unknown"
        }
    except Exception as e:
        logger.error(f"Error in root endpoint: {e}")
        return {"message": "API Running", "error": str(e)}

# Simple health check (without prefix)
@app.get("/health")
async def simple_health():
    return {
        "status": "healthy", 
        "service": "website-analyzer",
        "timestamp": time.time()
    }

# Handle all preflight OPTIONS requests
@app.options("/{full_path:path}")
async def handle_options(request: Request):
    logger.info(f"🔄 CORS preflight for: {request.url.path}")
    return JSONResponse(
        status_code=200,
        content={"message": "CORS preflight OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400"
        }
    )

# Enhanced exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Unhandled exception on {request.method} {request.url.path}:")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Exception message: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error - check server logs",
            "path": str(request.url.path),
            "method": request.method,
            "error_type": type(exc).__name__,
            "timestamp": time.time()
        }
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    logger.warning(f"🔍 404 Not Found: {request.method} {request.url.path}")
    
    return JSONResponse(
        status_code=404,
        content={
            "detail": f"Endpoint not found: {request.method} {request.url.path}",
            "available_endpoints": [
                "GET / - API info",
                "GET /health - Simple health check", 
                "GET /api/v1/health - Detailed health check",
                "POST /api/v1/analyze - Analyze single website",
                "GET /api/v1/analyze - List all analyses",
                "GET /api/v1/analyze/{id} - Get specific analysis",
                "GET /api/v1/reports - List reports",
                "GET /api/v1/reports/stats - Report statistics",
                "POST /api/v1/bulk/urls - Bulk analyze URLs",
                "POST /api/v1/bulk/upload - Upload file for bulk analysis",
                "GET /docs - Interactive API documentation"
            ],
            "tip": "Check the HTTP method and endpoint path",
            "timestamp": time.time()
        }
    )

@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc: HTTPException):
    logger.warning(f"🚫 405 Method Not Allowed: {request.method} {request.url.path}")
    
    return JSONResponse(
        status_code=405,
        content={
            "detail": f"Method {request.method} not allowed for {request.url.path}",
            "path": str(request.url.path),
            "method": request.method,
            "tip": "Check if you're using POST instead of GET or vice versa",
            "common_fixes": [
                "Use POST for /api/v1/analyze (not GET)",
                "Use GET for /api/v1/analyze to list (not POST)",
                "Use GET for /api/v1/reports/stats (not POST)"
            ],
            "timestamp": time.time()
        }
    )

# Add startup event for additional debugging
@app.on_event("startup")
async def debug_routes():
    """Log all registered routes for debugging"""
    logger.info("📋 Registered routes:")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods)
            logger.info(f"  {methods} {route.path}")

# Additional debug endpoint to test router registration
@app.get("/debug/routes")
async def debug_routes_endpoint():
    """Debug endpoint to show all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, 'name', 'unnamed')
            })
    
    return {
        "total_routes": len(routes),
        "routes": routes,
        "routers_included": [
            "health.router -> /api/v1",
            "analyze.router -> /api/v1", 
            "reports.router -> /api/v1",
            "bulk.router -> /api/v1"
        ]
    }
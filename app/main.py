"""Main FastAPI application for Website Analyzer"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager
import re
import time
import traceback
import logging
import sys
from app.utils.auth import verify_token
from app.utils.auth import get_password_hash

# Import your API routers - EXACTLY as they are in your project
from app.api import analyze, reports, health, bulk, leads, auth, proposals
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, init_db, get_database, COLLECTIONS
from datetime import datetime
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    try:
        logger.info("🚀 Starting Website Analyzer API...")
        logger.info(f"📍 Environment: {'Development' if settings.DEBUG else 'Production'}")
        # Avoid leaking DB credentials in logs; mask user/pass if present
        try:
            from urllib.parse import urlparse
            parsed = urlparse(settings.MONGODB_URL)
            safe_netloc = parsed.hostname or 'unknown-host'
            if parsed.port:
                safe_netloc += f":{parsed.port}"
            safe_db = (parsed.path or '').lstrip('/') or settings.DATABASE_NAME
            logger.info(f"🔧 Database: mongodb://{safe_netloc}/{safe_db}")
        except Exception:
            logger.info("🔧 Database: [redacted]")
        
        # Initialize database
        await init_db()
        logger.info("✅ Database initialized successfully")

        # Ensure default admin user exists and is up-to-date
        async def ensure_admin_user():
            try:
                db = get_database()
                email = "theanandsingh76@gmail.com"
                existing = await db[COLLECTIONS["users"]].find_one({"email": email})
                desired_hash = get_password_hash("AnandSingh@#12345@#Singh")
                if existing:
                    await db[COLLECTIONS["users"]].update_one(
                        {"_id": existing["_id"]},
                        {"$set": {
                            "hashed_password": desired_hash,
                            "is_active": True,
                            "is_verified": True,
                        }}
                    )
                    logger.info("🔄 Admin user ensured and updated")
                    return
                admin_doc = {
                    "email": email,
                    "name": "Admin",
                    "hashed_password": desired_hash,
                    "is_active": True,
                    "is_verified": True,
                    "created_at": datetime.utcnow(),
                    "last_login": None,
                }
                await db[COLLECTIONS["users"]].insert_one(admin_doc)
                logger.info("✅ Admin user created: theanandsingh76@gmail.com")
            except Exception as e:
                logger.error(f"⚠️ Failed to create admin user: {e}")

        # Ensure HR & Sales user exists
        async def ensure_hr_sales_user():
            try:
                db = get_database()
                email = "hr.nextinvision@gmail.com"
                existing = await db[COLLECTIONS["users"]].find_one({"email": email})
                if existing:
                    # Ensure credentials and status are correct
                    await db[COLLECTIONS["users"]].update_one(
                        {"_id": existing["_id"]},
                        {
                            "$set": {
                                "hashed_password": get_password_hash("NextinVision@#12345"),
                                "is_active": True,
                                "is_verified": True,
                            }
                        },
                    )
                    logger.info("🔄 HR & Sales user ensured and updated")
                    return
                user_doc = {
                    "email": email,
                    "name": "HR & Sales",
                    "hashed_password": get_password_hash("NextinVision@#12345"),
                    "is_active": True,
                    "is_verified": True,
                    "created_at": datetime.utcnow(),
                    "last_login": None,
                }
                await db[COLLECTIONS["users"]].insert_one(user_doc)
                logger.info("✅ HR & Sales user created: hr.nextinvision@gmail.com")
            except Exception as e:
                logger.error(f"⚠️ Failed to create HR & Sales user: {e}")

        await ensure_admin_user()
        await ensure_hr_sales_user()
        
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

# Updated CORS configuration using settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.(vercel\.app|run\.app)$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Global auth guard middleware (protect all endpoints except whitelisted)
@app.middleware("http")
async def enforce_authentication(request: Request, call_next):
    try:
        path = request.url.path
        method = request.method.upper()
        
        # Explicitly handle CORS preflight with correct headers for allowed origins
        if method == "OPTIONS":
            origin = request.headers.get("origin")
            request_headers = request.headers.get("access-control-request-headers", "*")
            response_headers = {
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": request_headers,
                "Access-Control-Max-Age": "86400",
            }
            is_allowed = bool(origin) and (
                origin in settings.ALLOWED_ORIGINS or re.match(r"https://.*\.(vercel\.app|run\.app)$", origin)
            )
            if is_allowed:
                response_headers["Access-Control-Allow-Origin"] = origin
                response_headers["Access-Control-Allow-Credentials"] = "true"
                response_headers["Vary"] = "Origin"
                return Response(status_code=204, headers=response_headers)
            # Not an allowed origin: let the request continue (will 404/405 without CORS headers)
            return await call_next(request)

        public_paths_prefix = [
            "/api/v1/auth",
            app.docs_url or "/docs",
            app.redoc_url or "/redoc",
            app.openapi_url or "/openapi.json",
        ]

        if any(path.startswith(prefix) for prefix in public_paths_prefix):
            return await call_next(request)

        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
        token = auth_header.split(" ", 1)[1].strip()
        # Will raise HTTPException(401) if invalid
        token_data = verify_token(token)

        # Enforce forced-logout by checking token iat against user's token_invalidated_at
        try:
            from jose import jwt
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            issued_at = payload.get("iat")
            if issued_at:
                db = get_database()
                from bson import ObjectId
                user = await db[COLLECTIONS["users"]].find_one({"_id": ObjectId(token_data.user_id)})
                invalidated_at = user.get("token_invalidated_at") if user else None
                if invalidated_at and issued_at < int(invalidated_at.timestamp()):
                    return JSONResponse(status_code=401, content={"detail": "Session expired. Please login again."})
                # Update last_seen_at for activity tracking
                await db[COLLECTIONS["users"]].update_one({"_id": user["_id"]}, {"$set": {"last_seen_at": datetime.utcnow()}})
        except Exception:
            # If this check fails, fall back to normal flow
            pass

        return await call_next(request)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "Invalid authentication"})


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

        # Ensure CORS headers are present on all responses for allowed origins
        origin = request.headers.get("origin")
        if origin:
            try:
                is_allowed = (
                    origin in settings.ALLOWED_ORIGINS or
                    re.match(r"https://.*\.(vercel\.app|run\.app)$", origin) is not None
                )
                if is_allowed:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
                    response.headers["Access-Control-Allow-Headers"] = "*"
                    # Don't over-set allow headers/methods here for non-OPTIONS
                    vary_val = response.headers.get("Vary")
                    response.headers["Vary"] = (vary_val + ", Origin") if vary_val else "Origin"
            except Exception as e:
                logger.error(f"CORS header setting error: {e}")
                pass
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
    app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])  # must register auth first
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])  # authenticated health
    app.include_router(analyze.router, prefix="/api/v1", tags=["Analysis"]) 
    app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
    app.include_router(bulk.router, prefix="/api/v1", tags=["Bulk Processing"])
    app.include_router(proposals.router, prefix="/api/v1", tags=["Proposals"])
    app.include_router(leads.router, prefix="/api/v1", tags=["Leads"])
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
                "bulk_status": "GET /api/v1/bulk/{id}/status",
                "leads": "GET /api/v1/leads",
                "lead_detail": "GET /api/v1/leads/{id}",
                "search_leads": "GET /api/v1/leads/search"
            },
            "cors": f"enabled_for_{len(settings.ALLOWED_ORIGINS)}_origins",
            "allowed_origins": settings.ALLOWED_ORIGINS,
            "database": "connected" if hasattr(app.state, 'db') else "unknown"
        }
    except Exception as e:
        logger.error(f"Error in root endpoint: {e}")
        return {"message": "API Running", "error": str(e)}

# CORS test endpoint
@app.options("/api/v1/cors-test")
async def cors_test_options():
    """Test CORS preflight request"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
        }
    )

@app.get("/api/v1/cors-test")
async def cors_test():
    """Test CORS response"""
    return {"message": "CORS is working", "timestamp": time.time()}

# Simple health check (without prefix)
@app.get("/health")
async def simple_health():
    return {
        "status": "healthy", 
        "service": "website-analyzer",
        "timestamp": time.time()
    }

# Let CORSMiddleware handle all preflight OPTIONS requests globally

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
            "bulk.router -> /api/v1",
            "leads.router -> /api/v1"
        ],
        "cors_origins": settings.ALLOWED_ORIGINS,
        "cors_enabled": True,
        "cors_middleware": "CORSMiddleware + Custom CORS handling"
    }

@app.get("/debug/cors")
async def debug_cors():
    """Debug CORS configuration"""
    return {
        "cors_enabled": True,
        "allowed_origins": settings.ALLOWED_ORIGINS,
        "origin_regex": r"https://.*\.(vercel\.app|run\.app)$",
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["*"],
        "expose_headers": ["*"],
        "max_age": 86400,
        "middleware_order": [
            "CORSMiddleware (FastAPI)",
            "Custom CORS handling (OPTIONS)",
            "Authentication middleware",
            "Request logging"
        ]
    }
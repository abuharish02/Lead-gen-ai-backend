# backend/app/api/analyze.py - SIMPLIFIED VERSION
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response
from app.models.analysis import AnalysisRequest, AnalysisResult, Analysis, AnalysisResponse
from app.services.analyzer import WebsiteAnalyzer
from app.database import get_db, COLLECTIONS
from datetime import datetime
from bson import ObjectId
import asyncio

router = APIRouter()

@router.post("/analyze", response_model=dict)
async def analyze_website(
    request: AnalysisRequest,
    db = Depends(get_db)
):
    """Analyze a single website"""
    try:
        # Check if analysis already exists
        existing = await db[COLLECTIONS["analyses"]].find_one({"url": request.url})
        if existing and existing.get("status") == "completed":
            return {
                "message": "Analysis already exists", 
                "analysis_id": str(existing["_id"])
            }
        
        # Create new analysis record
        analysis_data = {
            "url": request.url,
            "status": "processing",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db[COLLECTIONS["analyses"]].insert_one(analysis_data)
        analysis_id = result.inserted_id
        
        # Perform analysis
        analyzer = WebsiteAnalyzer()
        analysis_result = await analyzer.analyze_website(request.url)
        
        # Update analysis record with results
        update_data = {
            "updated_at": datetime.utcnow()
        }
        
        if 'error' in analysis_result:
            update_data["status"] = "failed"
            update_data["result_data"] = analysis_result
        else:
            update_data["status"] = "completed"
            update_data["result_data"] = analysis_result
            if analysis_result.get('company_name'):
                update_data["company_name"] = analysis_result['company_name']
            if analysis_result.get('industry'):
                update_data["industry"] = analysis_result['industry']
        
        await db[COLLECTIONS["analyses"]].update_one(
            {"_id": analysis_id},
            {"$set": update_data}
        )
        
        return {
            "analysis_id": str(analysis_id),
            "status": update_data["status"],
            "result": analysis_result
        }
        
    except Exception as e:
        # Update status to failed if analysis_id exists
        if 'analysis_id' in locals():
            await db[COLLECTIONS["analyses"]].update_one(
                {"_id": analysis_id},
                {"$set": {"status": "failed", "updated_at": datetime.utcnow()}}
            )
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/analyze")
async def list_analyses(skip: int = 0, limit: int = 100, db = Depends(get_db)):
    """List all analyses"""
    try:
        cursor = db[COLLECTIONS["analyses"]].find().skip(skip).limit(limit).sort("created_at", -1)
        analyses = await cursor.to_list(length=limit)
        
        return [
            {
                "id": str(a["_id"]),
                "url": a["url"],
                "company_name": a.get("company_name"),
                "industry": a.get("industry"),
                "status": a["status"],
                "created_at": a["created_at"]
            }
            for a in analyses
        ]
    except Exception as e:
        print(f"❌ Error listing analyses: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list analyses: {str(e)}")

@router.get("/analyze/{analysis_id}")
async def get_analysis(analysis_id: str, db = Depends(get_db)):
    """Get analysis result by ID"""
    try:
        # Convert string ID to ObjectId
        object_id = ObjectId(analysis_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")
    
    analysis = await db[COLLECTIONS["analyses"]].find_one({"_id": object_id})
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "id": str(analysis["_id"]),
        "url": analysis["url"],
        "company_name": analysis.get("company_name"),
        "industry": analysis.get("industry"),
        "status": analysis["status"],
        "result": analysis.get("result_data"),
        "created_at": analysis["created_at"],
        "updated_at": analysis["updated_at"]
    }

@router.delete("/analyze/{analysis_id}")
async def delete_analysis(analysis_id: str, db = Depends(get_db)):
    """Delete an analysis"""
    try:
        object_id = ObjectId(analysis_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")
    
    result = await db[COLLECTIONS["analyses"]].delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {"message": "Analysis deleted successfully"}
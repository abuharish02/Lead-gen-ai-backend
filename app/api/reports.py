# backend/app/api/reports.py - SIMPLIFIED VERSION
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import FileResponse
from app.services.report_generator import ReportGenerator
from app.services.excel_processor import ExcelProcessor
from app.database import get_db, COLLECTIONS
from bson import ObjectId
from datetime import datetime
from app.utils.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])

@router.get("/reports")
async def list_reports(skip: int = 0, limit: int = 100, db = Depends(get_db)):
    """List all completed analyses/reports"""
    try:
        cursor = db[COLLECTIONS["analyses"]].find(
            {"status": "completed"}
        ).skip(skip).limit(limit).sort("created_at", -1)
        
        analyses = await cursor.to_list(length=limit)
        
        return [
            {
                "id": str(a["_id"]),
                "url": a["url"],
                "company_name": a.get("company_name"),
                "industry": a.get("industry"),
                "digital_maturity_score": a.get("result_data", {}).get('digital_maturity_score', 0),
                "urgency_score": a.get("result_data", {}).get('urgency_score', 0),
                "created_at": a["created_at"]
            }
            for a in analyses
        ]
    except Exception as e:
        print(f"❌ Error listing reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")

@router.get("/reports/{analysis_id}/pdf")
async def download_pdf_report(analysis_id: str, db = Depends(get_db)):
    """Download PDF report for specific analysis"""
    try:
        object_id = ObjectId(analysis_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")
    
    analysis = await db[COLLECTIONS["analyses"]].find_one({"_id": object_id})
    if not analysis or analysis.get("status") != "completed":
        raise HTTPException(status_code=404, detail="Completed analysis not found")
    
    try:
        generator = ReportGenerator()
        result_data = analysis.get("result_data", {}) or {}
        # Merge top-level metadata with result data for comprehensive PDF
        merged = {
            **result_data,
            "url": analysis.get("url", result_data.get("url")),
            "company_name": analysis.get("company_name") or result_data.get("company_name"),
            "industry": analysis.get("industry") or result_data.get("industry"),
            "status": analysis.get("status"),
            "created_at": analysis.get("created_at"),
            "updated_at": analysis.get("updated_at"),
        }
        pdf_data = generator.generate_pdf_report(merged)
        
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=analysis_{analysis_id}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

@router.get("/reports/export/csv")
async def export_csv_report(db = Depends(get_db)):
    """Export all completed analyses as CSV"""
    cursor = db[COLLECTIONS["analyses"]].find({"status": "completed"})
    analyses = await cursor.to_list(length=None)
    
    if not analyses:
        raise HTTPException(status_code=404, detail="No completed analyses found")
    
    try:
        generator = ReportGenerator()
        results_data = [a.get("result_data", {}) for a in analyses if a.get("result_data")]
        csv_data = generator.generate_csv_data(results_data)
        
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=website_analyses.csv"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}")

@router.get("/reports/export/excel")
async def export_excel_report(db = Depends(get_db)):
    """Export all completed analyses as Excel"""
    cursor = db[COLLECTIONS["analyses"]].find({"status": "completed"})
    analyses = await cursor.to_list(length=None)
    
    if not analyses:
        raise HTTPException(status_code=404, detail="No completed analyses found")
    
    try:
        processor = ExcelProcessor()
        results_data = [a.get("result_data", {}) for a in analyses if a.get("result_data")]
        excel_data = processor.create_results_excel(results_data)
        
        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=website_analyses.xlsx"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel export failed: {str(e)}")

@router.delete("/reports/{analysis_id}")
async def delete_report(analysis_id: str, db = Depends(get_db)):
    """Delete specific analysis/report"""
    try:
        object_id = ObjectId(analysis_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")
    
    result = await db[COLLECTIONS["analyses"]].delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {"message": "Analysis deleted successfully"}

@router.get("/reports/stats")
async def get_report_stats(db = Depends(get_db)):
    """Get statistics about analyses"""
    try:
        # Use aggregation pipeline for better performance
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        cursor = db[COLLECTIONS["analyses"]].aggregate(pipeline)
        status_counts = {doc["_id"]: doc["count"] async for doc in cursor}
        
        total = sum(status_counts.values())
        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)
        processing = status_counts.get("processing", 0)
        
        success_rate = round((completed / total * 100) if total > 0 else 0, 2)
        
        return {
            "total_analyses": total,
            "completed": completed,
            "failed": failed,
            "processing": processing,
            "success_rate": success_rate
        }
    except Exception as e:
        print(f"❌ Error getting report stats: {str(e)}")
        # Fallback to simple counts if aggregation fails
        total = await db[COLLECTIONS["analyses"]].count_documents({})
        completed = await db[COLLECTIONS["analyses"]].count_documents({"status": "completed"})
        failed = await db[COLLECTIONS["analyses"]].count_documents({"status": "failed"})
        processing = await db[COLLECTIONS["analyses"]].count_documents({"status": "processing"})
        
        return {
            "total_analyses": total,
            "completed": completed,
            "failed": failed,
            "processing": processing,
            "success_rate": round((completed / total * 100) if total > 0 else 0, 2)
        }
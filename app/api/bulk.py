# backend/app/api/bulk.py
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends
from typing import List, Dict, Any
from bson import ObjectId
from datetime import datetime
import tempfile
import os
import csv
import io
import json
import uuid
from app.database import get_database
from app.models.analysis import Analysis
from app.services.analyzer import WebsiteAnalyzer
from app.utils.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])

# In-memory tracking for bulk operations (consider Redis for production)
bulk_operations = {}

@router.post("/bulk/upload")
async def upload_bulk_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload CSV/Excel file for bulk processing"""
    
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    try:
        content = await file.read()
        
        # Parse file based on extension
        if file.filename.endswith('.csv'):
            urls = parse_csv_content(content.decode('utf-8'))
        else:
            # Handle Excel files (you'll need to implement this)
            urls = parse_excel_content(content, file.filename)
        
        if not urls:
            raise HTTPException(status_code=400, detail="No valid URLs found in file")
        
        # Start bulk analysis
        return await bulk_analyze_urls(background_tasks, urls)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")

@router.post("/bulk/urls")
async def bulk_analyze_urls(
    background_tasks: BackgroundTasks,
    request_data: Dict[str, List[str]]
):
    """Analyze multiple URLs provided directly"""
    
    # Handle both {"urls": [...]} and direct list
    if isinstance(request_data, dict) and "urls" in request_data:
        urls = request_data["urls"]
    elif isinstance(request_data, list):
        urls = request_data
    else:
        raise HTTPException(status_code=400, detail="Expected {'urls': [list]} or direct list")
    
    if not urls or len(urls) > 500:
        raise HTTPException(status_code=400, detail="Provide 1-500 URLs")
    
    # Validate URLs
    valid_urls = []
    for url in urls:
        if isinstance(url, str) and url.strip():
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url.strip()
            valid_urls.append(url.strip())
    
    if not valid_urls:
        raise HTTPException(status_code=400, detail="No valid URLs provided")
    
    try:
        db = get_database()
        
        # Create bulk operation tracking
        bulk_id = str(uuid.uuid4())
        
        # Create analysis records in MongoDB
        analysis_ids = []
        for url in valid_urls:
            analysis_doc = {
                "url": url,
                "status": "pending",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "company_name": None,
                "industry": None,
                "result_data": None
            }
            
            result = await db.analyses.insert_one(analysis_doc)
            analysis_ids.append(str(result.inserted_id))
        
        # Track bulk operation
        bulk_operations[bulk_id] = {
            "bulk_id": bulk_id,
            "status": "processing",
            "total_urls": len(valid_urls),
            "completed": 0,
            "failed": 0,
            "analysis_ids": analysis_ids,
            "urls": valid_urls,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Start background processing
        background_tasks.add_task(process_bulk_analyses, bulk_id, valid_urls, analysis_ids)
        
        return {
            "bulk_id": bulk_id,
            "message": f"Bulk processing started for {len(valid_urls)} URLs",
            "analysis_ids": analysis_ids,
            "total_urls": len(valid_urls),
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk processing failed: {str(e)}")

@router.get("/bulk/{bulk_id}/status")
async def get_bulk_status(bulk_id: str):
    """Get status of bulk processing operation"""
    
    if bulk_id not in bulk_operations:
        raise HTTPException(status_code=404, detail="Bulk operation not found")
    
    operation = bulk_operations[bulk_id]
    
    # Calculate progress
    progress_percentage = (operation["completed"] + operation["failed"]) / operation["total_urls"] * 100
    
    return {
        "bulk_id": bulk_id,
        "status": operation["status"],
        "total_urls": operation["total_urls"],
        "completed": operation["completed"],
        "failed": operation["failed"],
        "progress_percentage": round(progress_percentage, 1),
        "analysis_ids": operation["analysis_ids"],
        "created_at": operation["created_at"],
        "updated_at": operation["updated_at"]
    }

@router.get("/bulk/{bulk_id}/results")
async def get_bulk_results(bulk_id: str):
    """Get results of completed bulk analysis"""
    
    if bulk_id not in bulk_operations:
        raise HTTPException(status_code=404, detail="Bulk operation not found")
    
    operation = bulk_operations[bulk_id]
    
    if operation["status"] != "completed":
        raise HTTPException(status_code=400, detail="Bulk operation not yet completed")
    
    try:
        db = get_database()
        
        # Fetch all analysis results
        results = []
        for analysis_id in operation["analysis_ids"]:
            analysis = await db.analyses.find_one({"_id": ObjectId(analysis_id)})
            if analysis:
                results.append({
                    "analysis_id": str(analysis.get("_id")),
                    "url": analysis.get("url"),
                    "status": analysis.get("status"),
                    "company_name": analysis.get("company_name") or (analysis.get("result_data") or {}).get("company_name"),
                    "industry": analysis.get("industry") or (analysis.get("result_data") or {}).get("industry"),
                    "result_data": analysis.get("result_data") or {},
                    "created_at": analysis.get("created_at"),
                    "updated_at": analysis.get("updated_at")
                })
        
        return {
            "bulk_id": bulk_id,
            "status": operation["status"],
            "total_results": len(results),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch results: {str(e)}")

async def process_bulk_analyses(bulk_id: str, urls: List[str], analysis_ids: List[str]):
    """Background task to process bulk analyses"""
    
    try:
        db = get_database()
        analyzer = WebsiteAnalyzer()
        operation = bulk_operations[bulk_id]
        
        for i, (url, analysis_id) in enumerate(zip(urls, analysis_ids)):
            try:
                # Update status to processing
                await db.analyses.update_one(
                    {"_id": ObjectId(analysis_id)},
                    {
                        "$set": {
                            "status": "processing",
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                
                # Perform analysis
                analysis_result = await analyzer.analyze_website(url)
                
                if 'error' in analysis_result:
                    # Handle failed analysis
                    await db.analyses.update_one(
                        {"_id": ObjectId(analysis_id)},
                        {
                            "$set": {
                                "status": "failed",
                                "result_data": {"error": analysis_result['error']},
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    operation["failed"] += 1
                else:
                    # Handle successful analysis
                    result_data = analysis_result
                    await db.analyses.update_one(
                        {"_id": ObjectId(analysis_id)},
                        {
                            "$set": {
                                "status": "completed",
                                "result_data": result_data,
                                "company_name": result_data.get('company_name'),
                                "industry": result_data.get('industry'),
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    operation["completed"] += 1
                
                # Update bulk operation progress
                operation["updated_at"] = datetime.utcnow().isoformat()
                
            except Exception as e:
                # Handle individual URL failure
                await db.analyses.update_one(
                    {"_id": ObjectId(analysis_id)},
                    {
                        "$set": {
                            "status": "failed",
                            "result_data": {"error": str(e)},
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                operation["failed"] += 1
                operation["updated_at"] = datetime.utcnow().isoformat()
        
        # Mark bulk operation as completed
        operation["status"] = "completed"
        operation["updated_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        # Handle bulk operation failure
        if bulk_id in bulk_operations:
            bulk_operations[bulk_id]["status"] = "failed"
            bulk_operations[bulk_id]["error"] = str(e)
            bulk_operations[bulk_id]["updated_at"] = datetime.utcnow().isoformat()

def parse_csv_content(content: str) -> List[str]:
    """Parse URLs from CSV content"""
    urls = []
    
    try:
        # Handle both comma and other delimiters
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(content[:1024]).delimiter
        
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        
        for row in reader:
            # Look for URL in various column names
            url = None
            for key in ['url', 'URL', 'website', 'Website', 'domain', 'Domain']:
                if key in row and row[key] and row[key].strip():
                    url = row[key].strip()
                    break
            
            if url:
                # Clean and validate URL
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                urls.append(url)
    
    except Exception as e:
        # If CSV parsing fails, try simple line-by-line parsing
        lines = content.strip().split('\n')
        for line in lines[1:]:  # Skip header
            line = line.strip()
            if line and not line.startswith('#'):
                if not line.startswith(('http://', 'https://')):
                    line = 'https://' + line
                urls.append(line)
    
    return list(set(urls))  # Remove duplicates

def parse_excel_content(content: bytes, filename: str) -> List[str]:
    """Parse URLs from Excel content"""
    urls = []
    
    try:
        import pandas as pd
        
        # Save content to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Read Excel file
            df = pd.read_excel(tmp_file_path)
            
            # Look for URL columns
            url_columns = []
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['url', 'website', 'domain', 'link']):
                    url_columns.append(col)
            
            if url_columns:
                for col in url_columns:
                    for url in df[col].dropna():
                        url = str(url).strip()
                        if url and url != 'nan':
                            if not url.startswith(('http://', 'https://')):
                                url = 'https://' + url
                            urls.append(url)
            else:
                # If no URL column found, try first column
                first_col = df.columns[0]
                for url in df[first_col].dropna():
                    url = str(url).strip()
                    if url and url != 'nan':
                        if not url.startswith(('http://', 'https://')):
                            url = 'https://' + url
                        urls.append(url)
        
        finally:
            # Clean up temp file
            os.unlink(tmp_file_path)
    
    except ImportError:
        raise HTTPException(status_code=500, detail="pandas not installed - cannot process Excel files")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel parsing failed: {str(e)}")
    
    return list(set(urls))  # Remove duplicates

@router.get("/bulk/operations")
async def list_bulk_operations():
    """List all bulk operations"""
    
    try:
        operations = []
        for bulk_id, operation in bulk_operations.items():
            # Safely extract operation data
            op_data = {
                "bulk_id": bulk_id,
                "status": operation.get("status", "unknown"),
                "total_urls": operation.get("total_urls", 0),
                "completed": operation.get("completed", 0),
                "failed": operation.get("failed", 0),
                "created_at": operation.get("created_at", "")
            }
            operations.append(op_data)
        
        # Sort by created_at safely
        def sort_key(x):
            try:
                return x.get("created_at", "")
            except:
                return ""
        
        sorted_operations = sorted(operations, key=sort_key, reverse=True)
        
        return {
            "total_operations": len(operations),
            "operations": sorted_operations
        }
        
    except Exception as e:
        # Return safe response even if there's an error
        return {
            "total_operations": 0,
            "operations": [],
            "error": f"Failed to list operations: {str(e)}"
        }

@router.delete("/bulk/{bulk_id}")
async def delete_bulk_operation(bulk_id: str):
    """Delete a bulk operation and its associated analyses"""
    
    if bulk_id not in bulk_operations:
        raise HTTPException(status_code=404, detail="Bulk operation not found")
    
    try:
        db = get_database()
        operation = bulk_operations[bulk_id]
        
        # Delete associated analysis records
        analysis_ids = [ObjectId(aid) for aid in operation["analysis_ids"]]
        await db.analyses.delete_many({"_id": {"$in": analysis_ids}})
        
        # Remove from tracking
        del bulk_operations[bulk_id]
        
        return {
            "message": f"Bulk operation {bulk_id} and {len(analysis_ids)} analyses deleted"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

# Additional utility endpoints
@router.get("/bulk/{bulk_id}/export")
async def export_bulk_results(bulk_id: str, format: str = "json"):
    """Export bulk analysis results in various formats"""
    
    if bulk_id not in bulk_operations:
        raise HTTPException(status_code=404, detail="Bulk operation not found")
    
    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Supported formats: json, csv")
    
    try:
        db = get_database()
        operation = bulk_operations[bulk_id]
        
        # Fetch all results
        results = []
        for analysis_id in operation["analysis_ids"]:
            analysis = await db.analyses.find_one({"_id": ObjectId(analysis_id)})
            if analysis:
                result_data = analysis.get("result_data") or {}
                flat_result = {
                    "url": analysis.get("url", ""),
                    "status": analysis.get("status", ""),
                    "company_name": analysis.get("company_name") or result_data.get("company_name", ""),
                    "industry": analysis.get("industry") or result_data.get("industry", ""),
                    "business_purpose": result_data.get("business_purpose", ""),
                    "company_size": result_data.get("company_size", ""),
                    "digital_maturity_score": result_data.get("digital_maturity_score", 0),
                    "urgency_score": result_data.get("urgency_score", 0),
                    "potential_value": result_data.get("potential_value", ""),
                    "created_at": (analysis.get("created_at").isoformat() if analysis.get("created_at") else ""),
                }
                results.append(flat_result)
        
        if format == "csv":
            # Convert to CSV
            if not results:
                return {"message": "No results to export"}
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            
            from fastapi.responses import Response
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=bulk_analysis_{bulk_id}.csv"}
            )
        
        return {
            "bulk_id": bulk_id,
            "export_format": format,
            "total_results": len(results),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

# Health check for bulk operations
@router.get("/bulk/health")
async def bulk_health_check():
    """Health check for bulk analysis system"""
    
    try:
        db = get_database()
        
        # Count pending analyses
        pending_count = await db.analyses.count_documents({"status": "pending"})
        processing_count = await db.analyses.count_documents({"status": "processing"})
        
        return {
            "status": "healthy",
            "active_bulk_operations": len(bulk_operations),
            "pending_analyses": pending_count,
            "processing_analyses": processing_count,
            "total_operations_tracked": len(bulk_operations)
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
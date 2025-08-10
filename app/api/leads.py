# backend/app/api/leads.py
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from app.database import get_db, COLLECTIONS
from app.models.company import CompanyResponse
from app.models.analysis import AnalysisResponse
import logging
from app.utils.auth import get_current_active_user

logger = logging.getLogger(__name__)
logger.info("🔥 LEADS ROUTER LOADING...")

router = APIRouter(prefix="/leads", tags=["leads"], dependencies=[Depends(get_current_active_user)])
logger.info("🔥 LEADS ROUTER CREATED WITH PREFIX /leads")

# Debug route to confirm router is loaded
@router.get("/debug", response_model=dict)
async def debug_leads():
    """Debug route to test if leads router is working"""
    logger.info("🔥 DEBUG ROUTE CALLED!")
    return {"message": "Leads router is working!", "timestamp": "now"}

# Define the main leads function
async def get_leads_impl(
    db: AsyncIOMotorDatabase = Depends(get_db),
    limit: Optional[int] = 100,
    skip: Optional[int] = 0
):
    """
    Get all leads with contact details from completed analyses
    """
    try:
        logger.info(f"🔥 GET_LEADS_IMPL CALLED with limit={limit}, skip={skip}")
        
        # First, let's get a simple count to debug
        total_analyses = await db[COLLECTIONS["analyses"]].count_documents({"status": "completed"})
        logger.info(f"🔥 Total completed analyses: {total_analyses}")
        
        # Query completed analyses from the analyses collection
        # Use a simpler approach first - just get completed analyses
        pipeline = [
            {
                "$match": {
                    "status": "completed"
                }
            },
            {
                "$addFields": {
                    "name": "$company_name",
                    "website": "$url",
                    "contact_email": {
                        "$ifNull": [
                            "$result_data.contact_info.email",
                            "$contact_email"  # Fallback to top-level field if exists
                        ]
                    },
                    "contact_phone": {
                        "$ifNull": [
                            "$result_data.contact_info.phone",
                            "$contact_phone"  # Fallback to top-level field if exists
                        ]
                    },
                    "contact_address": {
                        "$ifNull": [
                            "$result_data.contact_info.address",
                            "$contact_address"  # Fallback to top-level field if exists
                        ]
                    },
                    "industry": "$industry",
                    "size": "$result_data.company_size",
                    "description": "$result_data.business_purpose",
                    "technologies": "$result_data.technologies",
                    "pain_points": "$result_data.pain_points",
                    "recommendations": "$result_data.recommendations",
                    "digital_maturity_score": "$result_data.digital_maturity_score",
                    "urgency_score": "$result_data.urgency_score",
                    "potential_value": "$result_data.potential_value",
                    "outreach_strategy": "$result_data.outreach_strategy"
                }
            },
            {
                "$project": {
                    "_id": 1,
                    # Common lead fields
                    "name": 1,
                    "website": 1,
                    "industry": 1,
                    "size": 1,
                    "description": 1,
                    "technologies": 1,
                    "contact_email": 1,
                    "contact_phone": 1,
                    "contact_address": 1,
                    "pain_points": 1,
                    "recommendations": 1,
                    "digital_maturity_score": 1,
                    "urgency_score": 1,
                    "potential_value": 1,
                    "outreach_strategy": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    # Convenience fields for frontend
                    "analysis_status": "$status",
                    "last_analyzed": "$updated_at",
                    # Tracking fields (may be null if not set)
                    "tracking": {"$ifNull": ["$tracking", {}]},
                    "tracking_stage": {"$ifNull": ["$tracking.stage", "new"]},
                    "proposal_generated": {"$ifNull": ["$tracking.proposal_generated", False]},
                    "proposal_sent": {"$ifNull": ["$tracking.proposal_sent", False]},
                    "proposal_sent_at": {"$ifNull": ["$tracking.proposal_sent_at", None]},
                    "next_follow_up_at": {"$ifNull": ["$tracking.next_follow_up_at", None]},
                    "last_contacted_at": {"$ifNull": ["$tracking.last_contacted_at", None]},
                    "notes": {"$ifNull": ["$tracking.notes", None]},
                }
            },
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        leads = await db[COLLECTIONS["analyses"]].aggregate(pipeline).to_list(length=limit)
        logger.info(f"🔥 Pipeline returned {len(leads)} leads")
        
        # Convert ObjectId to string for JSON serialization
        for lead in leads:
            if "_id" in lead:
                lead["id"] = str(lead["_id"])
                del lead["_id"]
        
        # Debug: Log first few leads
        if leads:
            logger.info(f"🔥 First lead sample: {leads[0]}")
        
        logger.info(f"🔥 RETURNING {len(leads)} LEADS")
        return leads
        
    except Exception as e:
        logger.error(f"Error fetching leads: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch leads")

# ✅ SUPPORT BOTH: with and without trailing slash
@router.get("", response_model=List[dict])
async def get_leads_no_slash(
    db: AsyncIOMotorDatabase = Depends(get_db),
    limit: Optional[int] = 100,
    skip: Optional[int] = 0
):
    """Get all leads - no trailing slash version"""
    logger.info("🔥 GET_LEADS_NO_SLASH CALLED")
    return await get_leads_impl(db, limit, skip)

@router.get("/", response_model=List[dict]) 
async def get_leads_with_slash(
    db: AsyncIOMotorDatabase = Depends(get_db),
    limit: Optional[int] = 100,
    skip: Optional[int] = 0
):
    """Get all leads - with trailing slash version"""
    logger.info("🔥 GET_LEADS_WITH_SLASH CALLED")
    return await get_leads_impl(db, limit, skip)

@router.get("/search", response_model=List[dict])
async def search_leads(
    query: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    limit: Optional[int] = 50
):
    """
    Search leads by company name, website, or industry
    """
    try:
        logger.info(f"🔥 SEARCH_LEADS CALLED with query: {query}")
        
        # Search in completed analyses
        search_query = {
            "status": "completed",
            "$or": [
                {"company_name": {"$regex": query, "$options": "i"}},
                {"url": {"$regex": query, "$options": "i"}},
                {"industry": {"$regex": query, "$options": "i"}},
                {"result_data.contact_info.email": {"$regex": query, "$options": "i"}}
            ]
        }
        
        pipeline = [
            {"$match": search_query},
            {
                "$addFields": {
                    "name": "$company_name",
                    "website": "$url",
                    "contact_email": {
                        "$ifNull": [
                            "$result_data.contact_info.email",
                            "$contact_email"
                        ]
                    },
                    "contact_phone": {
                        "$ifNull": [
                            "$result_data.contact_info.phone",
                            "$contact_phone"
                        ]
                    },
                    "contact_address": {
                        "$ifNull": [
                            "$result_data.contact_info.address",
                            "$contact_address"
                        ]
                    },
                    "industry": "$industry",
                    "size": "$result_data.company_size",
                    "description": "$result_data.business_purpose",
                    "technologies": "$result_data.technologies"
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "name": 1,
                    "website": 1,
                    "industry": 1,
                    "size": 1,
                    "description": 1,
                    "technologies": 1,
                    "contact_email": 1,
                    "contact_phone": 1,
                    "contact_address": 1,
                    "created_at": 1
                }
            },
            {"$limit": limit}
        ]
        
        leads = await db[COLLECTIONS["analyses"]].aggregate(pipeline).to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for lead in leads:
            if "_id" in lead:
                lead["id"] = str(lead["_id"])
                del lead["_id"]
        
        logger.info(f"🔥 SEARCH RETURNING {len(leads)} LEADS")
        return leads
        
    except Exception as e:
        logger.error(f"Error searching leads: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search leads")

@router.get("/{lead_id}", response_model=dict)
async def get_lead_detail(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get detailed information for a specific lead
    """
    try:
        logger.info(f"🔥 GET_LEAD_DETAIL CALLED for ID: {lead_id}")
        from bson import ObjectId
        
        # Get analysis information from analyses collection
        analysis = await db[COLLECTIONS["analyses"]].find_one({"_id": ObjectId(lead_id)})
        if not analysis or analysis.get("status") != "completed":
            raise HTTPException(status_code=404, detail="Lead not found")
        
        lead_data = {
            "id": str(analysis["_id"]),
            "name": analysis.get("company_name"),
            "website": analysis.get("url"),
            "industry": analysis.get("industry"),
            "size": analysis.get("result_data", {}).get("company_size"),
            "description": analysis.get("result_data", {}).get("business_purpose"),
            "technologies": analysis.get("result_data", {}).get("technologies", []),
            "contact_email": analysis.get("result_data", {}).get("contact_info", {}).get("email"),
            "contact_phone": analysis.get("result_data", {}).get("contact_info", {}).get("phone"),
            "contact_address": analysis.get("result_data", {}).get("contact_info", {}).get("address"),
            "pain_points": analysis.get("result_data", {}).get("pain_points", []),
            "recommendations": analysis.get("result_data", {}).get("recommendations", []),
            "digital_maturity_score": analysis.get("result_data", {}).get("digital_maturity_score"),
            "urgency_score": analysis.get("result_data", {}).get("urgency_score"),
            "potential_value": analysis.get("result_data", {}).get("potential_value"),
            "outreach_strategy": analysis.get("result_data", {}).get("outreach_strategy"),
            "created_at": analysis.get("created_at"),
            "updated_at": analysis.get("updated_at"),
            "analysis_status": analysis.get("status"),
            "last_analyzed": analysis.get("updated_at"),
            "tracking": analysis.get("tracking", {}),
        }
        
        logger.info(f"🔥 LEAD DETAIL RETURNED for: {lead_data.get('name', 'Unknown')}")
        return lead_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lead detail: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch lead detail")

logger.info("🔥 LEADS ROUTER FULLY LOADED!")


# -------- Lead Tracking --------

class LeadTrackingUpdate(BaseModel):
    stage: Optional[Literal[
        "new", "contacted", "qualified", "proposal_generated", "proposal_sent",
        "negotiation", "won", "lost"
    ]] = Field(None, description="Current stage in the sales pipeline")
    proposal_generated: Optional[bool] = None
    proposal_sent: Optional[bool] = None
    proposal_sent_at: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None
    next_follow_up_at: Optional[datetime] = None
    notes: Optional[str] = None


@router.get("/{lead_id}/tracking", response_model=Dict[str, Any])
async def get_lead_tracking(
    lead_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    from bson import ObjectId
    try:
        analysis = await db[COLLECTIONS["analyses"]].find_one({"_id": ObjectId(lead_id)})
        if not analysis:
            raise HTTPException(status_code=404, detail="Lead not found")
        tracking = analysis.get("tracking") or {}
        # Provide defaults for convenience
        tracking.setdefault("stage", "new")
        tracking.setdefault("proposal_generated", False)
        tracking.setdefault("proposal_sent", False)
        return tracking
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lead tracking: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch lead tracking")


@router.patch("/{lead_id}/tracking", response_model=Dict[str, Any])
async def update_lead_tracking(
    lead_id: str,
    payload: LeadTrackingUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    from bson import ObjectId
    try:
        update_data = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
        if not update_data:
            return {"updated": False}

        # Auto-derive stage from booleans if not provided
        if "stage" not in update_data:
            if update_data.get("proposal_sent"):
                update_data.setdefault("stage", "proposal_sent")
            elif update_data.get("proposal_generated"):
                update_data.setdefault("stage", "proposal_generated")

        update_payload = {
            "$set": {
                **{f"tracking.{k}": v for k, v in update_data.items()},
                "tracking.updated_at": datetime.utcnow(),
            }
        }

        result = await db[COLLECTIONS["analyses"]].update_one({"_id": ObjectId(lead_id)}, update_payload)
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Lead not found")

        # Return merged tracking
        doc = await db[COLLECTIONS["analyses"]].find_one({"_id": ObjectId(lead_id)}, {"tracking": 1})
        tracking = doc.get("tracking") or {}
        return tracking
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating lead tracking: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update lead tracking")
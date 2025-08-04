# backend/app/models/analysis.py
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic v2"""
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema, handler):
        field_schema.update(type="string")
        return field_schema


class Analysis(BaseModel):
    """MongoDB document model for analysis"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    url: str = Field(..., index=True)
    company_name: Optional[str] = None
    industry: Optional[str] = None
    status: str = Field(default="pending")  # pending, processing, completed, failed
    result_data: Optional[Dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AnalysisResult(BaseModel):
    """Analysis result data structure"""
    company_name: str
    industry: str
    business_purpose: str
    company_size: str
    technologies: List[str]
    contact_info: Dict[str, str]
    pain_points: List[str]
    recommendations: List[str]
    digital_maturity_score: float
    urgency_score: float
    potential_value: str
    outreach_strategy: str


class AnalysisRequest(BaseModel):
    """Request model for single analysis"""
    url: str


class BulkAnalysisRequest(BaseModel):
    """Request model for bulk analysis"""
    urls: List[str]


# Response models for API
class AnalysisResponse(BaseModel):
    """API response model for analysis"""
    id: str
    url: str
    company_name: Optional[str]
    industry: Optional[str]
    status: str
    result_data: Optional[AnalysisResult]
    created_at: datetime
    updated_at: datetime
# backend/app/models/company.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
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


class Company(BaseModel):
    """MongoDB document model for company"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., index=True)
    website: str = Field(..., index=True)  # Changed from website_url to website to match your schema
    industry: Optional[str] = None
    size: Optional[str] = None  # Changed from company_size to size to match your schema
    description: Optional[str] = None  # Added description field
    technologies: List[str] = []
    contact_email: Optional[str] = None  # Added contact_email field
    last_analyzed: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class CompanyProfile(BaseModel):
    """Pydantic model for company profile data"""
    name: str
    website: str  # Changed from 'domain' to 'website'
    industry: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = []
    contact_email: Optional[str] = None  # Added contact_email field


class CompanyResponse(BaseModel):
    """API response model for company"""
    id: str
    name: str
    website: str
    industry: Optional[str]
    size: Optional[str]
    description: Optional[str]
    technologies: List[str]
    contact_email: Optional[str]
    last_analyzed: datetime
    created_at: datetime
    updated_at: datetime





    
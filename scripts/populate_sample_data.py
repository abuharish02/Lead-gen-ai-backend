"""Populate database with sample data for testing"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import sessionmaker
from app.database import engine
from app.models.analysis import Analysis
from app.models.company import Company
from datetime import datetime
import json

def populate_sample_data():
    """Create sample analysis and company data"""
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    sample_companies = [
        {
            "name": "TechStartup Inc",
            "website": "https://techstartup.com",
            "industry": "Technology",
            "size": "startup",
            "contact_email": "hello@techstartup.com"
        },
        {
            "name": "Local Restaurant",
            "website": "https://localrestaurant.com", 
            "industry": "Food & Beverage",
            "size": "small",
            "contact_email": "info@localrestaurant.com"
        }
    ]
    
    sample_analyses = [
        {
            "url": "https://techstartup.com",
            "company_name": "TechStartup Inc",
            "industry": "Technology",
            "status": "completed",
            "result_data": {
                "rag_insights": {
                    "detected_industry": "technology",
                    "relevant_services": ["Web Development", "Cloud Services"],
                    "technology_opportunities": ["Performance optimization", "Mobile optimization"],
                    "confidence_score": 0.85
                },
                "analysis": {
                    "company_name": "TechStartup Inc",
                    "industry": "Technology", 
                    "business_purpose": "SaaS platform development",
                    "technologies": ["React", "Node.js", "AWS"],
                    "pain_points": ["Mobile optimization", "Performance issues"],
                    "recommendations": ["Mobile-first redesign", "Performance optimization"],
                    "digital_maturity_score": 7.5,
                    "urgency_score": 6.0,
                    "potential_value": "$25,000 - $50,000"
                }
            }
        }
    ]
    
    try:
        # Create companies
        for company_data in sample_companies:
            company = Company(**company_data)
            db.add(company)
        
        # Create analyses
        for analysis_data in sample_analyses:
            analysis = Analysis(**analysis_data)
            db.add(analysis)
        
        db.commit()
        print(f"✅ Created {len(sample_companies)} sample companies")
        print(f"✅ Created {len(sample_analyses)} sample analyses")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {str(e)}")
        db.rollback()
        raise
    
    finally:
        db.close()

if __name__ == "__main__":
    populate_sample_data()
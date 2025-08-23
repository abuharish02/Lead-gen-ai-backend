# backend/run.py
"""Development server runner for Website Analyzer"""
import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("🚀 Starting Website Analyzer API Server...")
    print(f"📍 Environment: {'Development' if settings.DEBUG else 'Production'}")
    print(f"🔧 Database: {settings.DATABASE_URL}")
    print(f"🧠 Knowledge Base: {settings.KNOWLEDGE_BASE_DIR}")
    print(f"🤖 Gemini Model: {settings.GEMINI_MODEL}")
    print("-" * 50)
    
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8080,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )

# backend/tests/test_analyzer.py
"""Tests for website analyzer with RAG integration"""
import pytest
from unittest.mock import patch, AsyncMock
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.analyzer import WebsiteAnalyzer

@pytest.fixture
def analyzer():
    """Create analyzer instance for testing"""
    return WebsiteAnalyzer()

@pytest.fixture
def sample_scraped_data():
    """Sample scraped website data"""
    return {
        'url': 'https://example.com',
        'title': 'Example Company - Web Development Services',
        'description': 'Professional web development and IT consulting',
        'content': 'We provide web development, mobile apps, and cloud solutions for healthcare companies. Our WordPress sites are fast and secure.',
        'contact_info': {
            'emails': ['info@example.com'], 
            'phones': ['1234567890']
        },
        'technologies': ['WordPress', 'PHP', 'MySQL'],
        'scraped_at': '2024-01-01T10:00:00'
    }

@pytest.fixture
def sample_rag_analysis():
    """Sample RAG analysis data"""
    return {
        "general_context": [
            {
                "category": "IT Services - Web Development",
                "content": "Service: Web Development. Pain points: Outdated website design, Poor mobile responsiveness. Solutions: Modern responsive web design, Performance optimization.",
                "similarity": 0.85,
                "keywords": ["website", "web app", "responsive"]
            }
        ],
        "technology_context": [
            {
                "category": "Technology - CMS - WORDPRESS",
                "content": "CMS: wordpress. Market share: 43.2%. Strengths: flexibility, plugin ecosystem. Issues: security vulnerabilities, performance. Opportunities: custom themes, performance optimization.",
                "similarity": 0.92,
                "metadata": {
                    "technology": "wordpress",
                    "type": "CMS",
                    "opportunities": ["custom themes", "performance optimization", "security hardening"]
                }
            }
        ],
        "industry_context": [
            {
                "category": "Industry - Healthcare",
                "content": "Industry: healthcare. Technologies: EMR systems, HIPAA compliance tools. Pain points: patient data security, system interoperability. High-value services: HIPAA compliance consulting, EMR integration.",
                "similarity": 0.78,
                "metadata": {
                    "industry": "healthcare",
                    "high_value_services": ["HIPAA compliance consulting", "EMR integration", "telehealth solutions"]
                }
            }
        ],
        "detected_industry": "healthcare",
        "analyzed_technologies": ["WordPress", "PHP", "MySQL"]
    }

@pytest.fixture
def sample_gemini_response():
    """Sample Gemini API response"""
    return {
        "company_name": "Example Company",
        "industry": "Healthcare",
        "business_purpose": "Healthcare IT consulting and web development",
        "company_size": "small",
        "technologies": ["WordPress", "PHP", "MySQL"],
        "contact_info": {"email": "info@example.com", "phone": "1234567890"},
        "pain_points": ["WordPress security vulnerabilities", "Mobile responsiveness issues"],
        "recommendations": ["Security hardening", "Mobile optimization", "Performance improvements"],
        "digital_maturity_score": 6.5,
        "urgency_score": 7.0,
        "potential_value": "$15,000 - $35,000",
        "outreach_strategy": "Focus on healthcare compliance and security benefits"
    }

@pytest.mark.asyncio
async def test_analyze_website_success(analyzer, sample_scraped_data, sample_gemini_response):
    """Test successful website analysis with RAG integration"""
    
    with patch.object(analyzer.scraper, 'scrape_website', return_value=sample_scraped_data), \
         patch.object(analyzer.gemini, 'analyze_website_content', return_value=sample_gemini_response), \
         patch.object(analyzer, '_perform_rag_analysis', new_callable=AsyncMock) as mock_rag:
        
        # Mock RAG analysis
        mock_rag.return_value = {
            "general_context": [{"category": "Web Development", "similarity": 0.8}],
            "technology_context": [{"category": "WordPress", "similarity": 0.9}],
            "industry_context": [{"category": "Healthcare", "similarity": 0.7}],
            "detected_industry": "healthcare"
        }
        
        result = await analyzer.analyze_website('https://example.com')
        
        # Verify basic analysis
        assert 'error' not in result
        assert result['url'] == 'https://example.com'
        assert result['page_title'] == 'Example Company - Web Development Services'
        assert 'company_name' in result
        
        # Verify RAG integration
        assert 'rag_insights' in result
        assert result['rag_insights']['detected_industry'] == 'healthcare'
        assert 'confidence_score' in result['rag_insights']
        
        # Verify knowledge base info
        assert 'knowledge_base_info' in result

@pytest.mark.asyncio
async def test_rag_analysis_industry_detection(analyzer, sample_scraped_data):
    """Test industry detection in RAG analysis"""
    
    # Test healthcare detection
    healthcare_content = "We provide EMR systems and HIPAA compliance for medical practices and hospitals."
    industry = analyzer._detect_industry(healthcare_content)
    assert industry == "healthcare"
    
    # Test finance detection  
    finance_content = "Banking solutions, investment platforms, and financial advisory services."
    industry = analyzer._detect_industry(finance_content)
    assert industry == "finance"
    
    # Test unknown industry
    generic_content = "We make things and sell stuff to people."
    industry = analyzer._detect_industry(generic_content)
    assert industry is None

@pytest.mark.asyncio
async def test_enhanced_prompt_creation(analyzer, sample_scraped_data, sample_rag_analysis):
    """Test creation of RAG-enhanced prompts"""
    
    enhanced_prompt = analyzer._create_enhanced_analysis_prompt(sample_scraped_data, sample_rag_analysis)
    
    # Verify prompt contains key elements
    assert "example.com" in enhanced_prompt
    assert "Example Company" in enhanced_prompt
    assert "Detected Industry: Healthcare" in enhanced_prompt
    assert "TECHNOLOGY INSIGHTS:" in enhanced_prompt
    assert "wordpress" in enhanced_prompt.lower()
    assert "ANALYSIS REQUIREMENTS:" in enhanced_prompt

@pytest.mark.asyncio
async def test_analyze_website_scraping_error(analyzer):
    """Test handling of scraping errors"""
    
    scraping_error = {'error': 'Failed to scrape website'}
    
    with patch.object(analyzer.scraper, 'scrape_website', return_value=scraping_error):
        result = await analyzer.analyze_website('https://invalid-url.com')
        
        assert 'error' in result
        assert result['error'] == 'Failed to scrape website'

@pytest.mark.asyncio
async def test_confidence_score_calculation(analyzer):
    """Test confidence score calculation"""
    
    # High confidence scenario
    high_confidence_rag = {
        "general_context": [{"similarity": 0.9}, {"similarity": 0.8}],
        "detected_industry": "healthcare",
        "technology_context": [{"similarity": 0.85}]
    }
    
    score = analyzer._calculate_confidence_score(high_confidence_rag)
    assert score >= 0.8  # Should be high confidence
    
    # Low confidence scenario
    low_confidence_rag = {
        "general_context": [{"similarity": 0.2}],
        "detected_industry": None,
        "technology_context": []
    }
    
    score = analyzer._calculate_confidence_score(low_confidence_rag)
    assert score <= 0.5  # Should be low confidence

@pytest.mark.asyncio
async def test_extract_relevant_services(analyzer, sample_rag_analysis):
    """Test extraction of relevant services from RAG analysis"""
    
    services = analyzer._extract_relevant_services(sample_rag_analysis)
    
    assert isinstance(services, list)
    assert len(services) <= 5  # Should limit to 5 services
    # Should extract from metadata
    assert any("HIPAA compliance consulting" in str(services) for _ in [True])

@pytest.mark.asyncio 
async def test_technology_opportunities_extraction(analyzer, sample_rag_analysis):
    """Test extraction of technology opportunities"""
    
    opportunities = analyzer._extract_tech_opportunities(sample_rag_analysis)
    
    assert isinstance(opportunities, list)
    assert len(opportunities) <= 5  # Should limit to 5 opportunities
    # Should include WordPress opportunities
    expected_opportunities = ["custom themes", "performance optimization", "security hardening"]
    assert any(opp in opportunities for opp in expected_opportunities)

def test_industry_benchmarks_extraction(analyzer, sample_rag_analysis):
    """Test extraction of industry benchmarks"""
    
    benchmarks = analyzer._extract_industry_benchmarks(sample_rag_analysis)
    
    assert isinstance(benchmarks, dict)
    if "common_technologies" in benchmarks:
        assert isinstance(benchmarks["common_technologies"], list)
    if "typical_pain_points" in benchmarks:
        assert isinstance(benchmarks["typical_pain_points"], list)

# Integration test
@pytest.mark.asyncio
async def test_full_rag_pipeline(analyzer, sample_scraped_data):
    """Test the complete RAG analysis pipeline"""
    
    with patch.object(analyzer.knowledge_base, 'get_relevant_context', new_callable=AsyncMock) as mock_context, \
         patch.object(analyzer.knowledge_base, 'get_technology_context', return_value=[]), \
         patch.object(analyzer.knowledge_base, 'get_industry_specific_context', return_value=[]):
        
        # Mock knowledge base response
        mock_context.return_value = [
            {
                "category": "IT Services - Web Development",
                "content": "Web development services and solutions",
                "similarity": 0.85,
                "keywords": ["web", "development"]
            }
        ]
        
        rag_analysis = await analyzer._perform_rag_analysis(sample_scraped_data)
        
        # Verify RAG analysis structure
        assert "general_context" in rag_analysis
        assert "technology_context" in rag_analysis
        assert "industry_context" in rag_analysis
        assert "detected_industry" in rag_analysis
        assert "analyzed_technologies" in rag_analysis
        
        # Verify technology detection
        assert "WordPress" in rag_analysis["analyzed_technologies"]
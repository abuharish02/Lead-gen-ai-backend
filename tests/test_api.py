# backend/tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_analyze_endpoint():
    """Test analyze endpoint"""
    with patch('app.services.analyzer.WebsiteAnalyzer.analyze_website') as mock_analyze:
        mock_analyze.return_value = {
            'company_name': 'Test Company',
            'industry': 'Technology',
            'digital_maturity_score': 8.5
        }
        
        response = client.post(
            "/api/v1/analyze",
            json={"url": "https://example.com"}
        )
        
        assert response.status_code == 200
        assert "analysis_id" in response.json()
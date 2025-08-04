# backend/tests/test_scraper.py
import pytest
from unittest.mock import Mock, patch
from app.services.scraper import WebScraper

@pytest.fixture
def scraper():
    return WebScraper()

def test_scrape_website_success(scraper):
    """Test successful website scraping"""
    mock_response = Mock()
    mock_response.content = b'<html><head><title>Test Company</title></head><body><p>Web development services</p></body></html>'
    mock_response.headers = {'server': 'nginx'}
    
    with patch.object(scraper.session, 'get', return_value=mock_response):
        result = scraper.scrape_website('https://example.com')
        
        assert 'error' not in result
        assert result['title'] == 'Test Company'
        assert 'nginx' in result['technologies'][0].lower()

def test_scrape_website_invalid_url(scraper):
    """Test scraping with invalid URL"""
    with patch.object(scraper.session, 'get', side_effect=Exception('Invalid URL')):
        result = scraper.scrape_website('invalid-url')
        
        assert 'error' in result
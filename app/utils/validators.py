# backend/app/utils/validators.py
import re
from urllib.parse import urlparse
from typing import List, Optional

class URLValidator:
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate if URL is properly formatted"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL format"""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    @staticmethod
    def validate_urls(urls: List[str]) -> tuple[List[str], List[str]]:
        """Validate list of URLs, return valid and invalid ones"""
        valid_urls = []
        invalid_urls = []
        
        for url in urls:
            normalized = URLValidator.normalize_url(url)
            if URLValidator.is_valid_url(normalized):
                valid_urls.append(normalized)
            else:
                invalid_urls.append(url)
        
        return valid_urls, invalid_urls
    
    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return None
# backend/app/utils/extractors.py
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

class DataExtractor:
    @staticmethod
    def extract_company_info(text: str, title: str = "") -> Dict[str, str]:
        """Extract basic company information from text"""
        # Common company keywords
        company_indicators = [
            r'(?:Inc\.?|LLC|Corp\.?|Corporation|Ltd\.?|Limited|Co\.?|Company)',
            r'(?:Solutions|Services|Systems|Technologies|Tech)',
            r'(?:Consulting|Agency|Studio|Group|Partners)'
        ]
        
        company_name = ""
        if title:
            # Try to extract from title first
            for indicator in company_indicators:
                match = re.search(rf'([A-Z][A-Za-z\s&]+{indicator})', title, re.IGNORECASE)
                if match:
                    company_name = match.group(1).strip()
                    break
        
        if not company_name:
            # Fallback to first few words of title
            words = title.split()[:3] if title else []
            company_name = " ".join(words)
        
        return {
            "company_name": company_name,
            "extracted_from": "title" if title else "content"
        }
    
    @staticmethod
    def extract_contact_details(soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract contact information from BeautifulSoup object"""
        text = soup.get_text()
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = list(set(re.findall(email_pattern, text)))
        
        # Phone patterns
        phone_patterns = [
            r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            r'\+?[1-9]\d{1,14}',  # International format
            r'\(\d{3}\)\s*\d{3}-\d{4}'  # US format with parentheses
        ]
        
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))
        
        # Clean phone numbers
        clean_phones = []
        for phone in phones:
            if isinstance(phone, tuple):
                phone = ''.join(phone)
            clean_phone = re.sub(r'[^\d+]', '', str(phone))
            if len(clean_phone) >= 10:
                clean_phones.append(clean_phone)
        
        return {
            "emails": emails[:5],  # Limit to 5 emails
            "phones": list(set(clean_phones))[:3]  # Limit to 3 unique phones
        }
    
    @staticmethod
    def extract_social_links(soup: BeautifulSoup) -> Dict[str, str]:
        """Extract social media links"""
        social_platforms = {
            'linkedin': r'linkedin\.com/(?:company|in)/',
            'facebook': r'facebook\.com/',
            'twitter': r'(?:twitter\.com|x\.com)/',
            'instagram': r'instagram\.com/',
            'youtube': r'youtube\.com/'
        }
        
        social_links = {}
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href'].lower()
            for platform, pattern in social_platforms.items():
                if re.search(pattern, href):
                    social_links[platform] = link['href']
                    break
        
        return social_links
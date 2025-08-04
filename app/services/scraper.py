# backend/app/services/scraper.py
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional

class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_website(self, url: str) -> Dict:
        """Scrape website content and metadata"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            return {
                'url': url,
                'title': self._get_title(soup),
                'description': self._get_description(soup),
                'content': self._get_content(soup),
                'contact_info': self._extract_contact_info(soup),
                'technologies': self._detect_technologies(response, soup),
                'images': self._get_images(soup, url),
                'links': self._get_links(soup, url)
            }
        except Exception as e:
            return {'error': str(e), 'url': url}
    
    def _get_title(self, soup: BeautifulSoup) -> str:
        title = soup.find('title')
        return title.text.strip() if title else ""
    
    def _get_description(self, soup: BeautifulSoup) -> str:
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        return meta_desc.get('content', '') if meta_desc else ""
    
    def _get_content(self, soup: BeautifulSoup) -> str:
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        return soup.get_text()[:5000]  # Limit content length
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        text = soup.get_text()
        return {
            'emails': re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text),
            'phones': re.findall(r'[\+]?[1-9]?[0-9]{7,12}', text)[:5]  # Limit results
        }
    
    def _detect_technologies(self, response, soup: BeautifulSoup) -> List[str]:
        technologies = []
        
        # Check server headers
        server = response.headers.get('server', '').lower()
        if 'nginx' in server:
            technologies.append('Nginx')
        if 'apache' in server:
            technologies.append('Apache')
        
        # Check for common frameworks/CMS
        text = soup.get_text().lower()
        if 'wordpress' in text:
            technologies.append('WordPress')
        if 'shopify' in text:
            technologies.append('Shopify')
        
        return technologies
    
    def _get_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        images = []
        for img in soup.find_all('img', src=True)[:10]:  # Limit to 10 images
            src = img['src']
            if src.startswith('http'):
                images.append(src)
            else:
                images.append(urljoin(base_url, src))
        return images
    
    def _get_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        links = []
        for link in soup.find_all('a', href=True)[:20]:  # Limit to 20 links
            href = link['href']
            if href.startswith('http'):
                links.append(href)
            elif not href.startswith('#'):
                links.append(urljoin(base_url, href))
        return links
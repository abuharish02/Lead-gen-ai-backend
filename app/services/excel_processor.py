# backend/app/services/excel_processor.py
import pandas as pd
from typing import List, Dict, Any
import asyncio
from .analyzer import WebsiteAnalyzer

class ExcelProcessor:
    def __init__(self):
        self.analyzer = WebsiteAnalyzer()
    
    def read_excel_urls(self, file_path: str) -> List[str]:
        """Extract URLs from Excel file"""
        try:
            df = pd.read_excel(file_path)
            # Look for URL column
            url_columns = [col for col in df.columns if 'url' in col.lower() or 'website' in col.lower()]
            
            if url_columns:
                urls = df[url_columns[0]].dropna().tolist()
                return [str(url) for url in urls if str(url).startswith(('http://', 'https://'))]
            
            # If no URL column found, assume first column contains URLs
            return df.iloc[:, 0].dropna().tolist()
        except Exception as e:
            raise ValueError(f"Error reading Excel file: {str(e)}")
    
    async def process_bulk_analysis(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Process multiple URLs in batch"""
        results = []
        
        # Process in batches to avoid overwhelming the system
        batch_size = 5
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.analyzer.analyze_website(url) for url in batch],
                return_exceptions=True
            )
            
            for url, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results.append({'url': url, 'error': str(result)})
                else:
                    results.append(result)
        
        return results
    
    def create_results_excel(self, results: List[Dict[str, Any]]) -> bytes:
        """Create Excel file from analysis results"""
        # Flatten results for Excel export
        flattened_data = []
        for result in results:
            if 'error' not in result:
                flattened_data.append({
                    'URL': result.get('url', ''),
                    'Company Name': result.get('company_name', ''),
                    'Industry': result.get('industry', ''),
                    'Business Purpose': result.get('business_purpose', ''),
                    'Company Size': result.get('company_size', ''),
                    'Digital Maturity Score': result.get('digital_maturity_score', 0),
                    'Urgency Score': result.get('urgency_score', 0),
                    'Potential Value': result.get('potential_value', ''),
                    'Technologies': ', '.join(result.get('technologies', [])),
                    'Pain Points': ', '.join(result.get('pain_points', [])),
                    'Recommendations': ', '.join(result.get('recommendations', []))
                })
        
        df = pd.DataFrame(flattened_data)
        
        # Convert to Excel bytes
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        return buffer.getvalue()
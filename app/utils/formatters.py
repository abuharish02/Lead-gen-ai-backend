# backend/app/utils/formatters.py
from typing import Dict, Any, List
import json
from datetime import datetime

class DataFormatter:
    @staticmethod
    def format_analysis_result(raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format and clean analysis result"""
        formatted = {
            "company_name": raw_result.get("company_name", "Unknown"),
            "industry": raw_result.get("industry", "Not specified"),
            "business_purpose": raw_result.get("business_purpose", ""),
            "company_size": raw_result.get("company_size", "Unknown"),
            "technologies": DataFormatter._clean_list(raw_result.get("technologies", [])),
            "contact_info": DataFormatter._clean_contact_info(raw_result.get("contact_info", {})),
            "pain_points": DataFormatter._clean_list(raw_result.get("pain_points", [])),
            "recommendations": DataFormatter._clean_list(raw_result.get("recommendations", [])),
            "digital_maturity_score": DataFormatter._clean_score(raw_result.get("digital_maturity_score", 0)),
            "urgency_score": DataFormatter._clean_score(raw_result.get("urgency_score", 0)),
            "potential_value": raw_result.get("potential_value", "To be determined"),
            "outreach_strategy": raw_result.get("outreach_strategy", ""),
            "formatted_at": datetime.utcnow().isoformat()
        }
        
        return formatted
    
    @staticmethod
    def _clean_list(items: Any) -> List[str]:
        """Clean and validate list items"""
        if not isinstance(items, list):
            return []
        
        cleaned = []
        for item in items:
            if isinstance(item, str) and item.strip():
                cleaned.append(item.strip())
            elif item:
                cleaned.append(str(item).strip())
        
        return cleaned[:10]  # Limit to 10 items
    
    @staticmethod
    def _clean_contact_info(contact_info: Any) -> Dict[str, str]:
        """Clean and validate contact information"""
        if not isinstance(contact_info, dict):
            return {}
        
        cleaned = {}
        for key, value in contact_info.items():
            if isinstance(value, str) and value.strip():
                cleaned[key] = value.strip()
            elif isinstance(value, list) and value:
                cleaned[key] = value[0] if value[0] else ""
        
        return cleaned
    
    @staticmethod
    def _clean_score(score: Any) -> float:
        """Clean and validate score values"""
        try:
            score_float = float(score)
            return max(0.0, min(10.0, score_float))  # Clamp between 0-10
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def format_for_export(results: List[Dict[str, Any]], format_type: str = "csv") -> Dict[str, Any]:
        """Format results for different export types"""
        if format_type == "csv":
            return DataFormatter._format_for_csv(results)
        elif format_type == "excel":
            return DataFormatter._format_for_excel(results)
        else:
            return {"error": "Unsupported format type"}
    
    @staticmethod
    def _format_for_csv(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format results for CSV export"""
        formatted_rows = []
        
        for result in results:
            row = {
                "Company Name": result.get("company_name", ""),
                "Industry": result.get("industry", ""),
                "Business Purpose": result.get("business_purpose", ""),
                "Company Size": result.get("company_size", ""),
                "Digital Maturity Score": result.get("digital_maturity_score", 0),
                "Urgency Score": result.get("urgency_score", 0),
                "Potential Value": result.get("potential_value", ""),
                "Technologies": ", ".join(result.get("technologies", [])),
                "Pain Points": "; ".join(result.get("pain_points", [])),
                "Recommendations": "; ".join(result.get("recommendations", [])),
                "Contact Email": result.get("contact_info", {}).get("email", ""),
                "Contact Phone": result.get("contact_info", {}).get("phone", "")
            }
            formatted_rows.append(row)
        
        return {"rows": formatted_rows, "format": "csv"}
    
    @staticmethod
    def _format_for_excel(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format results for Excel export with multiple sheets"""
        # Main summary sheet
        summary_rows = []
        detailed_rows = []
        
        for result in results:
            summary_row = {
                "Company": result.get("company_name", ""),
                "Industry": result.get("industry", ""),
                "Size": result.get("company_size", ""),
                "Digital Score": result.get("digital_maturity_score", 0),
                "Urgency Score": result.get("urgency_score", 0),
                "Value": result.get("potential_value", "")
            }
            summary_rows.append(summary_row)
            
            detailed_row = {
                **summary_row,
                "Business Purpose": result.get("business_purpose", ""),
                "Technologies": ", ".join(result.get("technologies", [])),
                "Pain Points": "; ".join(result.get("pain_points", [])),
                "Recommendations": "; ".join(result.get("recommendations", [])),
                "Contact Info": json.dumps(result.get("contact_info", {})),
                "Outreach Strategy": result.get("outreach_strategy", "")
            }
            detailed_rows.append(detailed_row)
        
        return {
            "summary": summary_rows,
            "detailed": detailed_rows,
            "format": "excel"
        }
# backend/app/services/report_generator.py
from typing import Dict, Any, List
import json
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

class ReportGenerator:
    def generate_pdf_report(self, analysis: Dict[str, Any]) -> bytes:
        """Generate PDF report from analysis data"""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, f"Website Analysis Report")
        
        # Company info
        c.setFont("Helvetica", 12)
        y = 720
        c.drawString(50, y, f"Company: {analysis.get('company_name', 'N/A')}")
        y -= 20
        c.drawString(50, y, f"Industry: {analysis.get('industry', 'N/A')}")
        y -= 20
        c.drawString(50, y, f"URL: {analysis.get('url', 'N/A')}")
        
        # Scores
        y -= 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Analysis Scores")
        y -= 20
        c.setFont("Helvetica", 12)
        c.drawString(50, y, f"Digital Maturity: {analysis.get('digital_maturity_score', 0)}/10")
        y -= 20
        c.drawString(50, y, f"Urgency Score: {analysis.get('urgency_score', 0)}/10")
        
        # Recommendations
        y -= 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Recommendations")
        y -= 20
        c.setFont("Helvetica", 10)
        
        for rec in analysis.get('recommendations', [])[:5]:
            c.drawString(60, y, f"• {rec[:80]}")
            y -= 15
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_csv_data(self, analyses: List[Dict[str, Any]]) -> str:
        """Generate CSV data from multiple analyses"""
        csv_lines = []
        csv_lines.append("Company,Industry,URL,Digital Maturity,Urgency Score,Potential Value")
        
        for analysis in analyses:
            line = f"{analysis.get('company_name', '')},{analysis.get('industry', '')},{analysis.get('url', '')},{analysis.get('digital_maturity_score', 0)},{analysis.get('urgency_score', 0)},{analysis.get('potential_value', '')}"
            csv_lines.append(line)
        
        return "\n".join(csv_lines)
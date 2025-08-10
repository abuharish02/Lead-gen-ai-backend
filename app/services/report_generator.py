# backend/app/services/report_generator.py
from typing import Dict, Any, List
import json
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import simpleSplit
import io


class ReportGenerator:
    def _ensure_space(self, c: canvas.Canvas, current_y: int, required: int) -> int:
        """Start a new page if not enough vertical space remains; return possibly reset y."""
        if current_y - required < 60:  # bottom margin
            c.showPage()
            c.setFont("Helvetica", 12)
            return 750
        return current_y

    def _draw_section_title(self, c: canvas.Canvas, title: str, y: int) -> int:
        y = self._ensure_space(c, y, 30)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, title)
        c.setFont("Helvetica", 12)
        return y - 22

    def _draw_wrapped_text(self, c: canvas.Canvas, text: str, y: int, max_width: int = 500, line_height: int = 14) -> int:
        if not text:
            return y
        lines = simpleSplit(str(text), "Helvetica", 12, max_width)
        for line in lines:
            y = self._ensure_space(c, y, line_height)
            c.drawString(50, y, line)
            y -= line_height
        return y

    def _draw_bullets(self, c: canvas.Canvas, items: List[str], y: int, max_items: int = 10) -> int:
        if not items:
            return y
        for item in items[:max_items]:
            y = self._ensure_space(c, y, 16)
            lines = simpleSplit(str(item), "Helvetica", 12, 480)
            if lines:
                c.drawString(60, y, f"• {lines[0]}")
                y -= 16
                for cont in lines[1:]:
                    y = self._ensure_space(c, y, 16)
                    c.drawString(75, y, cont)
                    y -= 16
        return y

    def generate_pdf_report(self, analysis: Dict[str, Any]) -> bytes:
        """Generate PDF report from analysis data with comprehensive sections."""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 770, "Website Analysis Report")
        c.setFont("Helvetica", 10)
        c.drawRightString(560, 770, datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

        y = 740
        c.setFont("Helvetica", 12)

        # Company Information
        y = self._draw_section_title(c, "Company Information", y)
        y = self._draw_wrapped_text(c, f"Company: {analysis.get('company_name', 'N/A')}", y)
        y = self._draw_wrapped_text(c, f"Industry: {analysis.get('industry', 'N/A')}", y)
        y = self._draw_wrapped_text(c, f"URL: {analysis.get('url', 'N/A')}", y)
        if analysis.get('business_purpose'):
            y = self._draw_wrapped_text(c, f"Business Purpose: {analysis.get('business_purpose')}", y)
        if analysis.get('company_size'):
            y = self._draw_wrapped_text(c, f"Company Size: {analysis.get('company_size')}", y)

        # Scores
        y = self._draw_section_title(c, "Scores", y)
        y = self._draw_wrapped_text(c, f"Digital Maturity: {analysis.get('digital_maturity_score', 0)} / 10", y)
        y = self._draw_wrapped_text(c, f"Urgency Score: {analysis.get('urgency_score', 0)} / 10", y)
        if analysis.get('potential_value'):
            y = self._draw_wrapped_text(c, f"Potential Value: {analysis.get('potential_value')}", y)

        # Website Overview
        if analysis.get('page_title') or analysis.get('meta_description') or analysis.get('scraped_at'):
            y = self._draw_section_title(c, "Website Overview", y)
            if analysis.get('page_title'):
                y = self._draw_wrapped_text(c, f"Page Title: {analysis.get('page_title')}", y)
            if analysis.get('meta_description'):
                y = self._draw_wrapped_text(c, f"Meta Description: {analysis.get('meta_description')}", y)
            if analysis.get('scraped_at'):
                y = self._draw_wrapped_text(c, f"Scraped At: {analysis.get('scraped_at')}", y)

        # Technologies (combine detected_technologies + technologies)
        tech_list = []
        if isinstance(analysis.get('technologies'), list):
            tech_list.extend([str(t) for t in analysis.get('technologies')])
        if isinstance(analysis.get('detected_technologies'), list):
            tech_list.extend([str(t) for t in analysis.get('detected_technologies')])
        tech_list = list(dict.fromkeys(tech_list))  # unique preserve order
        if tech_list:
            y = self._draw_section_title(c, "Technologies", y)
            y = self._draw_wrapped_text(c, ", ".join(tech_list), y)

        # Contact Info
        contact = analysis.get('contact_info') or {}
        if isinstance(contact, dict) and contact:
            y = self._draw_section_title(c, "Contact Information", y)
            for key in ['email', 'phone', 'address']:
                if key in contact and contact[key]:
                    y = self._draw_wrapped_text(c, f"{key.title()}: {contact[key]}", y)
            # If contact info stored as lists
            for key in ['emails', 'phones']:
                if key in contact and isinstance(contact[key], list) and contact[key]:
                    y = self._draw_wrapped_text(c, f"{key.title()}: {', '.join(contact[key])}", y)

        # Media & Links
        if isinstance(analysis.get('images'), list) and analysis['images']:
            y = self._draw_section_title(c, "Images (URLs)", y)
            y = self._draw_bullets(c, [str(u) for u in analysis['images'][:6]], y, max_items=6)
        if isinstance(analysis.get('links'), list) and analysis['links']:
            y = self._draw_section_title(c, "Sample Links", y)
            y = self._draw_bullets(c, [str(u) for u in analysis['links'][:10]], y, max_items=10)

        # Pain Points
        if isinstance(analysis.get('pain_points'), list) and analysis['pain_points']:
            y = self._draw_section_title(c, "Identified Pain Points", y)
            y = self._draw_bullets(c, analysis['pain_points'], y, max_items=12)

        # Recommendations
        if isinstance(analysis.get('recommendations'), list) and analysis['recommendations']:
            y = self._draw_section_title(c, "Recommendations", y)
            y = self._draw_bullets(c, analysis['recommendations'], y, max_items=12)

        # Outreach Strategy
        if analysis.get('outreach_strategy'):
            y = self._draw_section_title(c, "Outreach Strategy", y)
            y = self._draw_wrapped_text(c, analysis.get('outreach_strategy'), y)

        # RAG Insights (optional summary)
        rag = analysis.get('rag_insights') or {}
        if isinstance(rag, dict) and rag:
            y = self._draw_section_title(c, "RAG Insights", y)
            if rag.get('detected_industry'):
                y = self._draw_wrapped_text(c, f"Detected Industry: {rag['detected_industry']}", y)
            if rag.get('relevant_services'):
                y = self._draw_wrapped_text(c, "Relevant Services:", y)
                y = self._draw_bullets(c, rag.get('relevant_services', []), y, max_items=8)
            if rag.get('technology_opportunities'):
                y = self._draw_wrapped_text(c, "Technology Opportunities:", y)
                y = self._draw_bullets(c, rag.get('technology_opportunities', []), y, max_items=8)
            if isinstance(rag.get('industry_benchmarks'), dict) and rag['industry_benchmarks']:
                common = rag['industry_benchmarks'].get('common_technologies')
                pain = rag['industry_benchmarks'].get('typical_pain_points')
                if common:
                    y = self._draw_wrapped_text(c, f"Common Technologies: {', '.join(common)}", y)
                if pain:
                    y = self._draw_wrapped_text(c, f"Typical Pain Points: {', '.join(pain)}", y)
            if rag.get('confidence_score') is not None:
                y = self._draw_wrapped_text(c, f"Confidence Score: {rag['confidence_score']}", y)

        # Knowledge Base Summary
        kb = analysis.get('knowledge_base_info') or {}
        if isinstance(kb, dict) and kb:
            y = self._draw_section_title(c, "Knowledge Base", y)
            if kb.get('total_items') is not None:
                y = self._draw_wrapped_text(c, f"Entries Loaded: {kb.get('total_items')}", y)
            if isinstance(kb.get('categories'), dict) and kb['categories']:
                parts = [f"{k}: {v}" for k, v in kb['categories'].items()]
                y = self._draw_wrapped_text(c, "Categories: " + ", ".join(parts), y)

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
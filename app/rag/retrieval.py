# backend/app/rag/retrieval.py
from typing import List, Dict, Any, Optional
import json
import os
from .embeddings import EmbeddingService
from .knowledge_base import KnowledgeBase

class RetrievalService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.knowledge_base = KnowledgeBase()
    
    async def retrieve_context(self, query: str, context_type: str = "general") -> Dict[str, Any]:
        """Retrieve relevant context for analysis"""
        # Get relevant knowledge base context
        kb_context = await self.knowledge_base.get_relevant_context(query)
        
        # Get industry-specific context if applicable
        industry_context = self._get_industry_context(query, context_type)
        
        # Get technology-specific context
        tech_context = self._get_technology_context(query)
        
        return {
            "knowledge_base": kb_context,
            "industry_specific": industry_context,
            "technology_specific": tech_context,
            "query": query,
            "context_type": context_type
        }
    
    def _get_industry_context(self, query: str, context_type: str) -> List[Dict[str, Any]]:
        """Get industry-specific context"""
        industry_patterns = {
            "healthcare": {
                "pain_points": ["HIPAA compliance", "patient data security", "telehealth integration"],
                "opportunities": ["digital health solutions", "patient portals", "medical records systems"]
            },
            "finance": {
                "pain_points": ["regulatory compliance", "data security", "legacy system integration"],
                "opportunities": ["fintech solutions", "mobile banking", "blockchain integration"]
            },
            "ecommerce": {
                "pain_points": ["payment processing", "inventory management", "mobile optimization"],
                "opportunities": ["marketplace integration", "analytics dashboards", "customer experience"]
            },
            "education": {
                "pain_points": ["remote learning", "student management", "content delivery"],
                "opportunities": ["learning management systems", "virtual classrooms", "assessment tools"]
            }
        }
        
        query_lower = query.lower()
        relevant_industries = []
        
        for industry, context in industry_patterns.items():
            if industry in query_lower or any(keyword in query_lower for keyword in context["pain_points"] + context["opportunities"]):
                relevant_industries.append({
                    "industry": industry,
                    "context": context
                })
        
        return relevant_industries
    
    def _get_technology_context(self, query: str) -> List[Dict[str, str]]:
        """Get technology-specific context"""
        tech_indicators = {
            "wordpress": "WordPress CMS - opportunities for custom themes, plugins, performance optimization",
            "shopify": "Shopify platform - opportunities for custom apps, integrations, design improvements",
            "react": "React framework - modern web development, component architecture, performance optimization",
            "php": "PHP backend - modernization opportunities, framework migration, performance improvements",
            "mysql": "MySQL database - optimization, migration to cloud, backup solutions",
            "aws": "AWS cloud services - migration, optimization, managed services implementation",
            "ssl": "SSL/Security - certificate management, security audits, compliance improvements"
        }
        
        query_lower = query.lower()
        relevant_tech = []
        
        for tech, description in tech_indicators.items():
            if tech in query_lower:
                relevant_tech.append({
                    "technology": tech,
                    "opportunities": description
                })
        
        return relevant_tech
    
    def enhance_analysis_prompt(self, base_prompt: str, context: Dict[str, Any]) -> str:
        """Enhance analysis prompt with retrieved context"""
        context_sections = []
        
        # Add knowledge base context
        if context.get("knowledge_base"):
            kb_items = [item["content"] for item in context["knowledge_base"]]
            context_sections.append(f"Relevant Knowledge: {'; '.join(kb_items)}")
        
        # Add industry context
        if context.get("industry_specific"):
            for industry_info in context["industry_specific"]:
                industry = industry_info["industry"]
                pain_points = industry_info["context"]["pain_points"]
                opportunities = industry_info["context"]["opportunities"]
                context_sections.append(
                    f"{industry.title()} Industry Context - "
                    f"Common Pain Points: {', '.join(pain_points)}; "
                    f"Opportunities: {', '.join(opportunities)}"
                )
        
        # Add technology context
        if context.get("technology_specific"):
            for tech_info in context["technology_specific"]:
                context_sections.append(
                    f"{tech_info['technology'].title()}: {tech_info['opportunities']}"
                )
        
        # Combine with base prompt
        if context_sections:
            enhanced_prompt = base_prompt + "\n\nAdditional Context:\n" + "\n".join(context_sections)
            enhanced_prompt += "\n\nUse this context to provide more targeted and relevant analysis."
            return enhanced_prompt
        
        return base_prompt
from typing import Dict, Any, List
from .scraper import WebScraper
from .gemini_client import GeminiClient
from app.rag.knowledge_base import KnowledgeBase  # Fixed import path
from app.rag.retrieval import RetrievalService  # Add retrieval service

class WebsiteAnalyzer:
    def __init__(self):
        self.scraper = WebScraper()
        self.gemini = GeminiClient()
        self.knowledge_base = KnowledgeBase()
        self.retrieval_service = RetrievalService()
    
    async def analyze_website(self, url: str) -> Dict[str, Any]:
        """Complete website analysis pipeline with enhanced RAG integration"""
        try:
            # Step 1: Scrape website
            scraped_data = self.scraper.scrape_website(url)
            if 'error' in scraped_data:
                return scraped_data
            
            # Step 2: Enhanced RAG analysis
            rag_analysis = await self._perform_rag_analysis(scraped_data)
            
            # Step 3: Generate enhanced prompt for Gemini
            enhanced_prompt = self._create_enhanced_analysis_prompt(scraped_data, rag_analysis)
            
            # Step 4: Analyze with Gemini using enhanced prompt
            analysis = self.gemini.analyze_website_content(enhanced_prompt)  # Now passes RAG-enhanced prompt!
            
            # Fallback: if Gemini failed or returned incomplete structure, synthesize from scraped + RAG
            if not analysis or 'error' in analysis or not self._is_analysis_complete(analysis):
                analysis = self._generate_fallback_analysis(scraped_data, rag_analysis)
            
            # Step 5: Post-process and enrich with RAG insights
            final_analysis = self._enrich_analysis_with_rag(analysis, scraped_data, rag_analysis)
            
            # Step 6: Normalize analysis to ensure consistent fields
            final_analysis = self._normalize_analysis(final_analysis, scraped_data, rag_analysis)
            
            return final_analysis
            
        except Exception as e:
            return {'error': f'Analysis failed: {str(e)}'}
    
    async def _perform_rag_analysis(self, scraped_data: Dict) -> Dict[str, Any]:
        """Perform comprehensive RAG analysis"""
        content = scraped_data.get('content', '')
        title = scraped_data.get('title', '')
        technologies = scraped_data.get('technologies', [])
        url = scraped_data.get('url', '')
        
        # Combine different content for analysis
        analysis_content = f"{title} {content}"
        
        # Get general context
        general_context = await self.knowledge_base.get_relevant_context(analysis_content, top_k=5)
        
        # Get technology-specific context
        tech_context = []
        for tech in technologies:
            tech_specific = self.knowledge_base.get_technology_context(tech)
            tech_context.extend(tech_specific)
        
        # Detect industry from content
        detected_industry = self._detect_industry(analysis_content)
        industry_context = []
        if detected_industry:
            industry_context = self.knowledge_base.get_industry_specific_context(detected_industry)
        
        # Get retrieval service context
        retrieval_context = await self.retrieval_service.retrieve_context(analysis_content)
        
        return {
            "general_context": general_context,
            "technology_context": tech_context,
            "industry_context": industry_context,
            "detected_industry": detected_industry,
            "retrieval_context": retrieval_context,
            "analyzed_technologies": technologies
        }
    
    def _detect_industry(self, content: str) -> str:
        """Detect industry from website content"""
        content_lower = content.lower()
        
        industry_keywords = {
            "healthcare": ["medical", "health", "doctor", "patient", "clinic", "hospital", "pharmacy"],
            "finance": ["bank", "financial", "investment", "loan", "credit", "insurance", "trading"],
            "retail": ["shop", "store", "product", "sale", "discount", "cart", "checkout", "ecommerce"],
            "manufacturing": ["manufacturing", "factory", "production", "industrial", "machinery"],
            "education": ["school", "university", "course", "student", "learning", "education"],
            "real_estate": ["property", "real estate", "home", "house", "rent", "buy", "realtor"],
            "restaurant": ["restaurant", "food", "menu", "dining", "cafe", "delivery", "catering"],
            "legal": ["law", "legal", "attorney", "lawyer", "court", "legal services"],
            "technology": ["software", "tech", "IT", "development", "programming", "digital"]
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return industry
        
        return None
    
    def _create_enhanced_analysis_prompt(self, scraped_data: Dict, rag_analysis: Dict) -> str:
        """Create enhanced analysis prompt with RAG context"""
        base_content = {
            "url": scraped_data.get("url", ""),
            "title": scraped_data.get("title", ""),
            "content": scraped_data.get("content", "")[:2000],  # Limit content length
            "technologies": scraped_data.get("technologies", []),
            "meta_description": scraped_data.get("description", "")
        }
        
        # Build enhanced prompt
        prompt = f"""
Analyze this website comprehensively using the provided context:

WEBSITE DATA:
URL: {base_content['url']}
Title: {base_content['title']}
Description: {base_content['meta_description']}
Technologies Detected: {', '.join(base_content['technologies'])}
Content Sample: {base_content['content']}

INDUSTRY CONTEXT:
"""
        
        # Add industry-specific insights
        if rag_analysis.get("detected_industry"):
            prompt += f"Detected Industry: {rag_analysis['detected_industry'].title()}\n"
            
            if rag_analysis.get("industry_context"):
                prompt += "Industry-Specific Knowledge:\n"
                for context in rag_analysis["industry_context"][:2]:  # Limit to avoid token limits
                    prompt += f"- {context.get('content', '')[:200]}...\n"
        
        # Add technology insights
        if rag_analysis.get("technology_context"):
            prompt += "\nTECHNOLOGY INSIGHTS:\n"
            for tech_context in rag_analysis["technology_context"][:3]:
                prompt += f"- {tech_context.get('content', '')[:200]}...\n"
        
        # Add general business insights
        if rag_analysis.get("general_context"):
            prompt += "\nRELEVANT BUSINESS INSIGHTS:\n"
            for context in rag_analysis["general_context"][:3]:
                prompt += f"- {context.get('content', '')[:200]}...\n"
        
        # Analysis instructions
        prompt += """
        
ANALYSIS REQUIREMENTS:
1. Business Overview: Summarize what this business does and their target market
2. Technology Assessment: Evaluate current technology stack and identify opportunities
3. Industry-Specific Pain Points: Identify likely challenges based on industry knowledge
4. Improvement Opportunities: Suggest specific, actionable improvements
5. Value Proposition: Recommend how our services can address their needs
6. Priority Recommendations: List top 3 recommendations with business impact

Use the provided context to make your analysis more targeted and relevant. Focus on actionable insights that demonstrate understanding of their industry and technology needs.
"""
        
        return prompt
    
    def _enrich_analysis_with_rag(self, analysis: Dict, scraped_data: Dict, rag_analysis: Dict) -> Dict:
        """Enrich analysis with RAG insights and metadata"""
        enriched_analysis = analysis.copy()
        
        # Add basic metadata
        enriched_analysis.update({
            'url': scraped_data.get('url'),
            'scraped_at': scraped_data.get('scraped_at'),
            'page_title': scraped_data.get('title'),
            'meta_description': scraped_data.get('description'),
            'detected_technologies': scraped_data.get('technologies', [])
        })
        
        # Add RAG-derived insights
        enriched_analysis['rag_insights'] = {
            'detected_industry': rag_analysis.get('detected_industry'),
            'relevant_services': self._extract_relevant_services(rag_analysis),
            'technology_opportunities': self._extract_tech_opportunities(rag_analysis),
            'industry_benchmarks': self._extract_industry_benchmarks(rag_analysis),
            'confidence_score': self._calculate_confidence_score(rag_analysis)
        }
        
        # Add knowledge base statistics
        kb_stats = self.knowledge_base.get_knowledge_stats()
        enriched_analysis['knowledge_base_info'] = kb_stats
        
        return enriched_analysis

    def _is_analysis_complete(self, analysis: Dict[str, Any]) -> bool:
        required_fields = [
            'company_name', 'industry', 'business_purpose', 'pain_points', 'recommendations',
            'digital_maturity_score', 'urgency_score'
        ]
        for field in required_fields:
            if field not in analysis or analysis.get(field) in [None, '', [], {}]:
                return False
        return True

    def _generate_fallback_analysis(self, scraped: Dict[str, Any], rag: Dict[str, Any]) -> Dict[str, Any]:
        """Create a reasonable analysis when LLM parsing fails. Uses scraped title/content and RAG context."""
        title = scraped.get('title') or scraped.get('page_title') or ''
        company_guess = title.split('-')[0].strip() if title else 'N/A'
        detected_industry = rag.get('detected_industry') or 'Unknown'
        pain_points = []
        # derive pain points from industry context if present
        for ctx in rag.get('industry_context', []):
            meta = ctx.get('metadata', {})
            if isinstance(meta.get('pain_points'), list):
                pain_points.extend(meta['pain_points'][:3])
        if not pain_points:
            pain_points = [
                'Limited online presence',
                'Performance optimization needed',
                'Missing analytics-driven decision making'
            ]
        recommendations = []
        for ctx in rag.get('technology_context', []):
            meta = ctx.get('metadata', {})
            if isinstance(meta.get('opportunities'), list):
                recommendations.extend(meta['opportunities'][:3])
        if not recommendations:
            recommendations = [
                'Improve website performance and SEO',
                'Implement analytics and conversion tracking',
                'Modernize tech stack where feasible'
            ]
        return {
            'company_name': company_guess if company_guess else 'N/A',
            'industry': detected_industry if detected_industry else 'Unknown',
            'business_purpose': scraped.get('description') or scraped.get('content', '')[:160] or 'N/A',
            'company_size': 'unknown',
            'technologies': scraped.get('technologies', []),
            'contact_info': scraped.get('contact_info', {}),
            'pain_points': pain_points,
            'recommendations': recommendations,
            'digital_maturity_score': 5.0,
            'urgency_score': 5.0,
            'potential_value': 'To be determined',
            'outreach_strategy': 'Introduce value with quick wins and an assessment call'
        }
    
    def _extract_relevant_services(self, rag_analysis: Dict) -> List[str]:
        """Extract relevant services from RAG analysis"""
        services = []
        
        # From general context
        for context in rag_analysis.get("general_context", []):
            if context.get("metadata", {}).get("solutions"):
                services.extend(context["metadata"]["solutions"][:2])
        
        # From industry context
        for context in rag_analysis.get("industry_context", []):
            if context.get("metadata", {}).get("high_value_services"):
                services.extend(context["metadata"]["high_value_services"][:2])
        
        return list(set(services))[:5]  # Limit and deduplicate
    
    def _extract_tech_opportunities(self, rag_analysis: Dict) -> List[str]:
        """Extract technology opportunities from RAG analysis"""
        opportunities = []
        
        for context in rag_analysis.get("technology_context", []):
            if context.get("metadata", {}).get("opportunities"):
                opportunities.extend(context["metadata"]["opportunities"][:2])
        
        return list(set(opportunities))[:5]
    
    def _extract_industry_benchmarks(self, rag_analysis: Dict) -> Dict[str, Any]:
        """Extract industry benchmarks and standards"""
        benchmarks = {}
        
        for context in rag_analysis.get("industry_context", []):
            metadata = context.get("metadata", {})
            if "technologies" in metadata:
                benchmarks["common_technologies"] = metadata["technologies"]
            if "pain_points" in metadata:
                benchmarks["typical_pain_points"] = metadata["pain_points"]
        
        return benchmarks
    
    def _calculate_confidence_score(self, rag_analysis: Dict) -> float:
        """Calculate confidence score based on RAG context quality"""
        score = 0.0
        
        # Base score for having context
        if rag_analysis.get("general_context"):
            score += 0.3
        
        # Industry detection bonus
        if rag_analysis.get("detected_industry"):
            score += 0.3
        
        # Technology context bonus
        if rag_analysis.get("technology_context"):
            score += 0.2
        
        # Context quality bonus (based on similarity scores)
        general_contexts = rag_analysis.get("general_context", [])
        if general_contexts:
            avg_similarity = sum(ctx.get("similarity", 0) for ctx in general_contexts) / len(general_contexts)
            score += min(avg_similarity, 0.2)  
        
        return min(score, 1.0)  

    def _normalize_analysis(self, analysis: Dict[str, Any], scraped: Dict[str, Any], rag: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure the final analysis has a complete structure even when the LLM response is partial."""
        normalized = analysis.copy()

        def ensure(key: str, default):
            if key not in normalized or normalized.get(key) in [None, '', [], {}]:
                normalized[key] = default

        # Company and industry
        title = scraped.get('title') or scraped.get('page_title') or ''
        company_guess = title.split('-')[0].strip() if title else 'N/A'
        ensure('company_name', company_guess)
        ensure('industry', rag.get('detected_industry') or 'Unknown')

        # Scores
        ensure('digital_maturity_score', 5.0)
        ensure('urgency_score', 5.0)

        # Purpose and size
        ensure('business_purpose', scraped.get('description') or scraped.get('content', '')[:160] or 'N/A')
        ensure('company_size', 'unknown')

        # Technologies
        if not normalized.get('technologies'):
            normalized['technologies'] = scraped.get('technologies', [])

        # Contact info
        ensure('contact_info', scraped.get('contact_info') or {})

        # Lists
        ensure('pain_points', ['Limited online presence', 'Performance optimization needed'])
        ensure('recommendations', ['Improve website performance and SEO', 'Implement analytics and tracking'])

        return normalized
# backend/rag/knowledge_base.py
import os
import json
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app.config import settings  # Fixed import path

class KnowledgeBase:
    def __init__(self):
        self.knowledge_dir = settings.KNOWLEDGE_BASE_DIR
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.knowledge_data = []
        self.embeddings = None
        self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """Load knowledge base from JSON files"""
        os.makedirs(self.knowledge_dir, exist_ok=True)
        
        # Load IT services knowledge
        it_services_file = os.path.join(self.knowledge_dir, "it_services_knowledge.json")
        if os.path.exists(it_services_file):
            with open(it_services_file, 'r') as f:
                it_services_data = json.load(f)
                self._process_it_services_data(it_services_data)
        
        # Load technology database
        tech_db_file = os.path.join(self.knowledge_dir, "technology_database.json")
        if os.path.exists(tech_db_file):
            with open(tech_db_file, 'r') as f:
                tech_data = json.load(f)
                self._process_technology_data(tech_data)
        
        # Load other knowledge files if they exist
        self._load_additional_knowledge_files()
        
        # Fallback to default data if no files found
        if not self.knowledge_data:
            self.knowledge_data = self._get_default_knowledge()
        
        # Generate embeddings
        self._generate_embeddings()
    
    def _process_it_services_data(self, data: Dict[str, Any]):
        """Process IT services knowledge data"""
        categories = data.get("categories", [])
        for category in categories:
            # Add category-specific knowledge
            self.knowledge_data.append({
                "category": f"IT Services - {category['name']}",
                "content": f"Service: {category['name']}. Pain points: {', '.join(category['pain_points'])}. Solutions: {', '.join(category['solutions'])}.",
                "keywords": category.get("keywords", []),
                "metadata": {
                    "service_type": category["name"],
                    "pain_points": category["pain_points"],
                    "solutions": category["solutions"],
                    "value_indicators": category.get("value_indicators", [])
                }
            })
        
        # Process industry profiles
        industry_profiles = data.get("industry_profiles", {})
        for industry, profile in industry_profiles.items():
            self.knowledge_data.append({
                "category": f"Industry - {industry.title()}",
                "content": f"Industry: {industry}. Technologies: {', '.join(profile['common_technologies'])}. Pain points: {', '.join(profile['typical_pain_points'])}. High-value services: {', '.join(profile['high_value_services'])}.",
                "keywords": [industry] + profile.get("common_technologies", []),
                "metadata": {
                    "industry": industry,
                    "technologies": profile["common_technologies"],
                    "pain_points": profile["typical_pain_points"],
                    "high_value_services": profile["high_value_services"]
                }
            })
    
    def _process_technology_data(self, data: Dict[str, Any]):
        """Process technology database"""
        # Process CMS platforms
        cms_platforms = data.get("cms_platforms", {})
        for cms, details in cms_platforms.items():
            self.knowledge_data.append({
                "category": f"Technology - CMS - {cms.upper()}",
                "content": f"CMS: {cms}. Market share: {details.get('market_share', 0)}%. Strengths: {', '.join(details.get('strengths', []))}. Issues: {', '.join(details.get('common_issues', []))}. Opportunities: {', '.join(details.get('upgrade_opportunities', []))}.",
                "keywords": [cms] + details.get("strengths", []),
                "metadata": {
                    "technology": cms,
                    "type": "CMS",
                    "market_share": details.get("market_share", 0),
                    "strengths": details.get("strengths", []),
                    "issues": details.get("common_issues", []),
                    "opportunities": details.get("upgrade_opportunities", [])
                }
            })
        
        # Process hosting providers
        hosting_providers = data.get("hosting_providers", {})
        for hosting_type, details in hosting_providers.items():
            self.knowledge_data.append({
                "category": f"Technology - Hosting - {hosting_type.replace('_', ' ').title()}",
                "content": f"Hosting: {hosting_type}. Indicators: {', '.join(details.get('indicators', []))}. Issues: {', '.join(details.get('typical_issues', []))}. Upgrade path: {details.get('upgrade_path', '')}.",
                "keywords": details.get("indicators", []),
                "metadata": {
                    "technology": hosting_type,
                    "type": "hosting",
                    "indicators": details.get("indicators", []),
                    "issues": details.get("typical_issues", []),
                    "upgrade_path": details.get("upgrade_path", "")
                }
            })
        
        # Process frameworks
        frameworks = data.get("frameworks", {})
        for framework, details in frameworks.items():
            self.knowledge_data.append({
                "category": f"Technology - Framework - {framework.title()}",
                "content": f"Framework: {framework}. Version indicators: {', '.join(details.get('version_indicators', []))}. Issues: {', '.join(details.get('common_issues', []))}. Opportunities: {', '.join(details.get('opportunities', []))}.",
                "keywords": [framework] + details.get("version_indicators", []),
                "metadata": {
                    "technology": framework,
                    "type": "framework",
                    "version_indicators": details.get("version_indicators", []),
                    "issues": details.get("common_issues", []),
                    "opportunities": details.get("opportunities", [])
                }
            })
    
    def _load_additional_knowledge_files(self):
        """Load other knowledge files like templates, benchmarks etc."""
        knowledge_files = [
            "industry_benchmark.json",
            "proposal_templates.json",
            "email_templates.json"
        ]
        
        for filename in knowledge_files:
            filepath = os.path.join(self.knowledge_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        # Process based on file type
                        if "benchmark" in filename:
                            self._process_benchmark_data(data, filename)
                        elif "template" in filename:
                            self._process_template_data(data, filename)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
    
    def _process_benchmark_data(self, data: Dict[str, Any], filename: str):
        """Process benchmark data"""
        # Add benchmark knowledge
        for key, value in data.items():
            if isinstance(value, (str, list, dict)):
                self.knowledge_data.append({
                    "category": f"Benchmark - {key}",
                    "content": str(value),
                    "keywords": [key],
                    "metadata": {"source": filename, "type": "benchmark"}
                })
    
    def _process_template_data(self, data: Dict[str, Any], filename: str):
        """Process template data"""
        # Add template knowledge
        for key, value in data.items():
            if isinstance(value, (str, dict)):
                self.knowledge_data.append({
                    "category": f"Template - {key}",
                    "content": str(value),
                    "keywords": [key],
                    "metadata": {"source": filename, "type": "template"}
                })
    
    def _get_default_knowledge(self):
        """Fallback default knowledge if no files are found"""
        return [
            {
                "category": "IT Services",
                "content": "Common IT services include web development, mobile app development, cloud migration, cybersecurity consulting, data analytics, and digital transformation.",
                "keywords": ["web development", "mobile app", "cloud", "security", "analytics"],
                "metadata": {"type": "default"}
            }
        ]
    
    def _generate_embeddings(self):
        """Generate embeddings for knowledge base content"""
        if not self.knowledge_data:
            return
        
        contents = [item["content"] for item in self.knowledge_data]
        self.embeddings = self.embedding_model.encode(contents)
    
    async def get_relevant_context(self, query: str, top_k: int = 5, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a query"""
        if not self.knowledge_data or self.embeddings is None:
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        # Get top-k most similar items above threshold
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        relevant_context = []
        for idx in top_indices:
            if similarities[idx] > threshold:
                context_item = {
                    "category": self.knowledge_data[idx]["category"],
                    "content": self.knowledge_data[idx]["content"],
                    "similarity": float(similarities[idx]),
                    "keywords": self.knowledge_data[idx].get("keywords", [])
                }
                
                # Include metadata if available
                if "metadata" in self.knowledge_data[idx]:
                    context_item["metadata"] = self.knowledge_data[idx]["metadata"]
                
                relevant_context.append(context_item)
        
        return relevant_context
    
    def get_industry_specific_context(self, industry: str) -> List[Dict[str, Any]]:
        """Get context specific to an industry"""
        industry_context = []
        for item in self.knowledge_data:
            if (f"Industry - {industry.title()}" in item["category"] or 
                industry.lower() in [kw.lower() for kw in item.get("keywords", [])]):
                industry_context.append(item)
        return industry_context
    
    def get_technology_context(self, technology: str) -> List[Dict[str, Any]]:
        """Get context specific to a technology"""
        tech_context = []
        for item in self.knowledge_data:
            if (f"Technology" in item["category"] and 
                technology.lower() in item["category"].lower()) or \
               technology.lower() in [kw.lower() for kw in item.get("keywords", [])]:
                tech_context.append(item)
        return tech_context
    
    def add_knowledge(self, category: str, content: str, keywords: List[str] = None, metadata: Dict = None):
        """Add new knowledge to the base"""
        new_item = {
            "category": category,
            "content": content,
            "keywords": keywords or [],
            "metadata": metadata or {}
        }
        
        self.knowledge_data.append(new_item)
        self._generate_embeddings()
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the loaded knowledge base"""
        if not self.knowledge_data:
            return {"total_items": 0, "categories": []}
        
        categories = {}
        for item in self.knowledge_data:
            category = item["category"].split(" - ")[0]  # Get main category
            categories[category] = categories.get(category, 0) + 1
        
        return {
            "total_items": len(self.knowledge_data),
            "categories": categories,
            "has_embeddings": self.embeddings is not None,
            "embedding_dimensions": self.embeddings.shape[1] if self.embeddings is not None else 0
        }
# backend/app/services/gemini_client.py
import google.generativeai as genai
from app.config import settings
from typing import Dict, Any, Union
import json
import re
import logging

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
    
    def analyze_website_content(self, prompt_or_data: Union[str, Dict]) -> Dict[str, Any]:
        """Analyze website content using Gemini with improved parsing"""
        
        # Handle both RAG-enhanced prompts (str) and legacy data (Dict)
        if isinstance(prompt_or_data, str):
            # RAG-enhanced prompt from analyzer
            prompt = self._enhance_prompt_for_json_output(prompt_or_data)
        else:
            # Legacy fallback - create structured prompt
            prompt = self._create_structured_analysis_prompt(prompt_or_data)
        
        try:
            response = self.model.generate_content(prompt)
            return self._parse_analysis_response_robust(response.text)
        except Exception as e:
            logger.info(f"Extracted structured data: {result['company_name']}, {result['industry']}")
        return result
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response for outreach and proposal content"""
        try:
            cleaned_text = self._clean_response_for_json(response_text)
            
            # Try multiple JSON extraction methods
            json_patterns = [
                r'```json\s*(\{.*?\})\s*```',
                r'```\s*(\{.*?\})\s*```',
                r'(\{(?:[^{}]|{[^{}]*})*\})'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, cleaned_text, re.DOTALL)
                for match in matches:
                    try:
                        return json.loads(match)
                    except json.JSONDecodeError:
                        continue
            
            # Try parsing entire response
            return json.loads(cleaned_text)
            
        except Exception as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            return {
                'error': 'Failed to parse JSON response',
                'raw_response': response_text[:500] + "..." if len(response_text) > 500 else response_text
            }
    
    def generate_targeted_outreach(self, analysis_data: Dict, template_type: str = "email") -> Dict[str, Any]:
        """Generate targeted outreach content based on analysis"""
        
        prompt = f"""
Generate a personalized {template_type} outreach based on this website analysis.

ANALYSIS DATA:
Company: {analysis_data.get('company_name', 'Unknown')}
Industry: {analysis_data.get('industry', 'Unknown')}
Business: {analysis_data.get('business_purpose', 'Unknown')}
Pain Points: {analysis_data.get('pain_points', [])}
Recommendations: {analysis_data.get('recommendations', [])}

Create personalized outreach that:
1. References specific observations about their business
2. Addresses their industry challenges
3. Offers relevant solutions
4. Includes compelling value proposition

You MUST respond with ONLY this JSON format:

{{
    "subject": "Compelling subject line referencing their business",
    "opening": "Personalized opening paragraph",
    "body": "Main message connecting their needs to our solutions",
    "call_to_action": "Specific next step request",
    "key_talking_points": ["point1", "point2", "point3"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            return {'error': f'Outreach generation failed: {str(e)}'}
    
    def enhance_analysis_with_rag(self, base_analysis: Dict, rag_context: Dict) -> Dict[str, Any]:
        """Enhance existing analysis with additional RAG insights"""
        
        prompt = f"""
Enhance this website analysis using additional business intelligence context.

ORIGINAL ANALYSIS:
{json.dumps(base_analysis, indent=2)}

ADDITIONAL CONTEXT:
Industry Knowledge: {rag_context.get('industry_context', [])}
Technology Insights: {rag_context.get('technology_context', [])}
Business Intelligence: {rag_context.get('general_context', [])}

Enhance the analysis by:
1. Adding more specific pain points based on industry knowledge
2. Refining recommendations with technology-specific opportunities  
3. Improving value proposition with industry benchmarks
4. Enhancing outreach strategy with context-aware messaging

You MUST respond with ONLY valid JSON in the same structure as the original analysis but with enhanced insights.
"""
        
        try:
            response = self.model.generate_content(prompt)
            enhanced = self._parse_analysis_response_robust(response.text)
            
            # Merge with original if enhancement fails
            if 'error' in enhanced:
                enhanced['original_analysis'] = base_analysis
                
            return enhanced
        except Exception as e:
            return {
                'error': f'RAG enhancement failed: {str(e)}', 
                'original_analysis': base_analysis
            }
    
    def generate_proposal_content(self, analysis_data: Dict, service_focus: str) -> Dict[str, Any]:
        """Generate proposal content based on analysis"""
        
        prompt = f"""
Create a professional service proposal based on this website analysis.

ANALYSIS:
Company: {analysis_data.get('company_name')}
Industry: {analysis_data.get('industry')}
Pain Points: {analysis_data.get('pain_points', [])}
Current Tech: {analysis_data.get('technologies', [])}

SERVICE FOCUS: {service_focus}

Generate proposal content including:
1. Executive Summary
2. Problem Statement (based on identified pain points)
3. Proposed Solution
4. Key Deliverables
5. Timeline Estimate
6. Investment Range
7. Expected ROI/Benefits

You MUST respond with ONLY this JSON format:

{{
    "executive_summary": "Compelling overview of opportunity",
    "problem_statement": "Identified challenges and their business impact",
    "proposed_solution": "Our comprehensive approach to address their needs",
    "key_deliverables": ["deliverable1", "deliverable2", "deliverable3"],
    "timeline": "Estimated timeframe (e.g., 8-12 weeks)",
    "investment_range": "Cost estimate range (e.g., $15K-30K)",
    "expected_benefits": ["benefit1", "benefit2", "benefit3"],
    "next_steps": "Recommended next actions"
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            return {'error': f'Proposal generation failed: {str(e)}'}
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Gemini API connection with JSON response validation"""
        try:
            test_prompt = """
Test the API connection. Respond with ONLY this JSON:

{
    "status": "connection_successful",
    "model": "gemini-1.5-flash",
    "timestamp": "2025-08-02T10:00:00Z"
}
"""
            response = self.model.generate_content(test_prompt)
            
            # Try to parse the response as JSON
            try:
                parsed_response = self._parse_json_response(response.text)
                return {
                    'status': 'success',
                    'response': parsed_response,
                    'raw_response': response.text,
                    'model': settings.GEMINI_MODEL
                }
            except:
                return {
                    'status': 'success_but_parsing_issue',
                    'raw_response': response.text,
                    'model': settings.GEMINI_MODEL,
                    'note': 'Connection works but JSON parsing needs improvement'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'model': settings.GEMINI_MODEL
            }.error(f"Gemini API error: {str(e)}")
            return {'error': f'Gemini API error: {str(e)}'}
    
    def _enhance_prompt_for_json_output(self, original_prompt: str) -> str:
        """Enhance existing prompt to ensure JSON output"""
        
        json_instruction = """

CRITICAL: You MUST respond with ONLY valid JSON in this exact format. No explanatory text before or after:

{
    "company_name": "Actual company name from website",
    "industry": "Primary industry/sector (e.g., Healthcare, Finance, Technology, Retail)",
    "business_purpose": "Clear description of what the company does",
    "company_size": "startup|small|medium|large|enterprise",
    "technologies": ["list", "of", "detected", "technologies"],
    "contact_info": {
        "email": "contact@company.com or null",
        "phone": "+1234567890 or null",
        "address": "Company address or null"
    },
    "pain_points": [
        "Specific business challenge 1",
        "Specific business challenge 2",
        "Specific business challenge 3"
    ],
    "recommendations": [
        "Actionable IT recommendation 1",
        "Actionable IT recommendation 2", 
        "Actionable IT recommendation 3"
    ],
    "digital_maturity_score": 7.5,
    "urgency_score": 6.0,
    "potential_value": "High/Medium/Low - brief explanation",
    "outreach_strategy": "Recommended approach for initial contact"
}

IMPORTANT RULES:
1. Return ONLY the JSON object - no markdown, no explanations
2. All string values must be properly quoted
3. Use null for missing contact information
4. Scores should be numbers between 1.0-10.0
5. Arrays should contain 2-5 relevant items
6. Focus on actionable, specific insights

"""
        
        return original_prompt + json_instruction
    
    def _create_structured_analysis_prompt(self, data: Dict) -> str:
        """Create structured analysis prompt with guaranteed JSON output"""
        
        content_sample = data.get('content', '')[:1500]  # Limit content to avoid token issues
        
        prompt = f"""
Analyze this website and extract business intelligence. Focus on identifying IT service opportunities.

WEBSITE DATA:
URL: {data.get('url', 'N/A')}
Title: {data.get('title', 'N/A')}
Meta Description: {data.get('description', 'N/A')}
Content: {content_sample}
Detected Technologies: {data.get('technologies', [])}

ANALYSIS INSTRUCTIONS:
1. Identify the company name from title, content, or branding
2. Determine the primary industry/business sector
3. Assess their current technology maturity
4. Identify potential IT challenges and pain points
5. Recommend specific IT services that could help them
6. Evaluate sales opportunity potential

You MUST respond with ONLY this JSON structure (no additional text):

{{
    "company_name": "Extract actual company name or 'Unknown'",
    "industry": "Primary business industry (Healthcare, Finance, Technology, etc.)",
    "business_purpose": "What the company does - be specific",
    "company_size": "startup|small|medium|large|enterprise",
    "technologies": ["wordpress", "cloudflare", "google-analytics"],
    "contact_info": {{
        "email": "contact@company.com",
        "phone": "+1234567890",
        "address": "123 Business St, City, State"
    }},
    "pain_points": [
        "Outdated website technology",
        "Poor mobile responsiveness", 
        "Limited digital marketing presence"
    ],
    "recommendations": [
        "Website modernization and optimization",
        "Implement responsive design",
        "SEO and digital marketing strategy"
    ],
    "digital_maturity_score": 6.5,
    "urgency_score": 7.0,
    "potential_value": "Medium - $10K-50K potential project value",
    "outreach_strategy": "Email introduction highlighting website improvements"
}}

CRITICAL: Return ONLY the JSON object above. No explanations, no markdown formatting, just pure JSON.
"""
        
        return prompt
    
    def _parse_analysis_response_robust(self, response_text: str) -> Dict[str, Any]:
        """Robust parsing with multiple fallback strategies"""
        
        # Strategy 1: Clean and extract JSON
        try:
            cleaned_text = self._clean_response_for_json(response_text)
            
            # Try to find JSON block
            json_patterns = [
                r'```json\s*(\{.*?\})\s*```',  # JSON in code block
                r'```\s*(\{.*?\})\s*```',      # JSON in generic code block
                r'(\{(?:[^{}]|{[^{}]*})*\})',  # Any JSON-like structure
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, cleaned_text, re.DOTALL)
                for match in matches:
                    try:
                        parsed = json.loads(match)
                        if self._validate_analysis_structure(parsed):
                            return parsed
                    except json.JSONDecodeError:
                        continue
            
            # Strategy 2: Try parsing the entire cleaned response
            try:
                parsed = json.loads(cleaned_text)
                if self._validate_analysis_structure(parsed):
                    return parsed
            except json.JSONDecodeError:
                pass
            
        except Exception as e:
            logger.warning(f"JSON parsing failed: {str(e)}")
        
        # Strategy 3: Structured text extraction
        logger.info("Falling back to structured text extraction")
        return self._extract_from_structured_text(response_text)
    
    def _clean_response_for_json(self, text: str) -> str:
        """Clean response text for JSON parsing"""
        
        # Remove markdown code block markers
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text)
        
        # Remove any leading/trailing explanatory text
        lines = text.split('\n')
        start_idx = 0
        end_idx = len(lines)
        
        # Find JSON start
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                start_idx = i
                break
        
        # Find JSON end (from the end)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().endswith('}'):
                end_idx = i + 1
                break
        
        cleaned = '\n'.join(lines[start_idx:end_idx])
        return cleaned.strip()
    
    def _validate_analysis_structure(self, data: Dict) -> bool:
        """Validate that parsed JSON has required structure"""
        
        required_fields = [
            'company_name', 'industry', 'business_purpose', 
            'pain_points', 'recommendations'
        ]
        
        # Check required fields exist
        if not all(field in data for field in required_fields):
            return False
        
        # Check data types
        if not isinstance(data.get('pain_points'), list):
            return False
        if not isinstance(data.get('recommendations'), list):
            return False
        
        # Check for reasonable content (not just empty or error strings)
        if data.get('company_name', '').strip() in ['', 'Unknown', 'N/A']:
            # Still valid, but lower quality
            pass
        
        return True
    
    def _extract_from_structured_text(self, text: str) -> Dict[str, Any]:
        """Extract structured data when JSON parsing completely fails"""
        
        # Default structure
        result = {
            "company_name": "Unknown",
            "industry": "Unknown", 
            "business_purpose": "Could not determine from analysis",
            "company_size": "unknown",
            "technologies": [],
            "contact_info": {},
            "pain_points": ["Analysis parsing incomplete"],
            "recommendations": ["Retry analysis with better prompt"],
            "digital_maturity_score": 5.0,
            "urgency_score": 5.0,
            "potential_value": "To be determined",
            "outreach_strategy": "Follow up for more information",
            "parsing_note": "Extracted from unstructured response"
        }
        
        # Enhanced extraction patterns
        extraction_patterns = {
            'company_name': [
                r"company[_\s]*name[:\s]*([^\n,}]+)",
                r"business[_\s]*name[:\s]*([^\n,}]+)",
                r"organization[:\s]*([^\n,}]+)"
            ],
            'industry': [
                r"industry[:\s]*([^\n,}]+)",
                r"sector[:\s]*([^\n,}]+)",
                r"business[_\s]*type[:\s]*([^\n,}]+)"
            ],
            'business_purpose': [
                r"business[_\s]*purpose[:\s]*([^\n}]+)",
                r"what[_\s]*company[_\s]*does[:\s]*([^\n}]+)",
                r"description[:\s]*([^\n}]+)"
            ]
        }
        
        # Apply extraction patterns
        for field, patterns in extraction_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip().strip('"').strip("'")
                    if value and value not in ["Unknown", "", "N/A", "-"]:
                        result[field] = value
                        break
        
        # Extract lists (pain points, recommendations)
        list_patterns = {
            'pain_points': r"pain[_\s]*points?[:\s]*\[(.*?)\]",
            'recommendations': r"recommendations?[:\s]*\[(.*?)\]"
        }
        
        for field, pattern in list_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    # Try to parse as JSON array
                    items = json.loads('[' + match.group(1) + ']')
                    result[field] = [item.strip().strip('"').strip("'") for item in items if item.strip()]
                except:
                    # Fallback: split by comma
                    items = match.group(1).split(',')
                    result[field] = [item.strip().strip('"').strip("'") for item in items if item.strip()]
        
        # Extract numeric scores
        score_patterns = {
            'digital_maturity_score': r"digital[_\s]*maturity[_\s]*score[:\s]*([0-9.]+)",
            'urgency_score': r"urgency[_\s]*score[:\s]*([0-9.]+)"
        }
        
        for field, pattern in score_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    if 1.0 <= score <= 10.0:
                        result[field] = score
                except ValueError:
                    pass
        
        logger
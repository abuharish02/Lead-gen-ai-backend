"""Setup and populate knowledge base files"""
import sys
import os
import json
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings

def setup_knowledge_base():
    """Create and populate all knowledge base files"""
    
    # Create knowledge base directory
    kb_dir = Path(settings.KNOWLEDGE_BASE_DIR)
    kb_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created knowledge base directory: {kb_dir}")
    
    # 1. IT Services Knowledge (Enhanced from your existing data)
    it_services_data = {
        "version": "1.0",
        "last_updated": "2024-01-01",
        "categories": [
            {
                "name": "Web Development",
                "keywords": ["website", "web app", "frontend", "backend", "responsive", "mobile-friendly"],
                "pain_points": [
                    "Outdated website design",
                    "Poor mobile responsiveness",
                    "Slow loading times", 
                    "Poor user experience",
                    "No content management system"
                ],
                "solutions": [
                    "Modern responsive web design",
                    "Performance optimization",
                    "CMS implementation",
                    "Mobile-first development", 
                    "User experience improvements"
                ],
                "value_indicators": ["high traffic", "e-commerce", "lead generation", "brand presence"]
            },
            {
                "name": "Cloud Services", 
                "keywords": ["cloud", "aws", "azure", "migration", "hosting", "scalability"],
                "pain_points": [
                    "On-premise infrastructure costs",
                    "Scalability limitations",
                    "Backup and disaster recovery issues",
                    "Security vulnerabilities",
                    "Maintenance overhead"
                ],
                "solutions": [
                    "Cloud migration strategy",
                    "Auto-scaling solutions",
                    "Managed cloud services",
                    "Backup automation",
                    "Cloud security implementation"
                ],
                "value_indicators": ["growing business", "remote work", "data storage needs"]
            },
            {
                "name": "Cybersecurity",
                "keywords": ["security", "ssl", "compliance", "audit", "firewall", "protection"],
                "pain_points": [
                    "Data breach risks",
                    "Compliance requirements", 
                    "Outdated security measures",
                    "Lack of security monitoring",
                    "Employee security training"
                ],
                "solutions": [
                    "Security audits and assessments",
                    "Multi-factor authentication",
                    "Security monitoring systems",
                    "Compliance consulting",
                    "Employee training programs"
                ],
                "value_indicators": ["financial data", "customer information", "regulatory industry"]
            },
            {
                "name": "Digital Transformation",
                "keywords": ["automation", "digital", "workflow", "efficiency", "modernization"],
                "pain_points": [
                    "Manual processes",
                    "Inefficient workflows",
                    "Poor data integration",
                    "Legacy system limitations", 
                    "Lack of analytics"
                ],
                "solutions": [
                    "Process automation",
                    "System integration",
                    "Data analytics implementation",
                    "Workflow optimization",
                    "Digital strategy consulting"
                ],
                "value_indicators": ["growth phase", "multiple systems", "manual processes"]
            }
        ],
        "industry_profiles": {
            "healthcare": {
                "common_technologies": ["EMR systems", "HIPAA compliance tools", "telemedicine platforms"],
                "typical_pain_points": ["patient data security", "system interoperability", "regulatory compliance"],
                "high_value_services": ["HIPAA compliance consulting", "EMR integration", "telehealth solutions"]
            },
            "finance": {
                "common_technologies": ["payment gateways", "CRM systems", "accounting software"],
                "typical_pain_points": ["regulatory compliance", "data security", "legacy system integration"],
                "high_value_services": ["fintech development", "compliance automation", "security audits"]
            },
            "retail": {
                "common_technologies": ["e-commerce platforms", "POS systems", "inventory management"],
                "typical_pain_points": ["omnichannel integration", "inventory tracking", "customer experience"],
                "high_value_services": ["e-commerce development", "inventory automation", "customer analytics"]
            },
            "manufacturing": {
                "common_technologies": ["ERP systems", "IoT sensors", "automation tools"],
                "typical_pain_points": ["production efficiency", "supply chain visibility", "quality control"],
                "high_value_services": ["IoT implementation", "ERP integration", "automation solutions"]
            }
        }
    }
    
    # 2. Technology Database
    technology_database = {
        "cms_platforms": {
            "wordpress": {
                "market_share": 43.2,
                "strengths": ["flexibility", "plugin ecosystem", "SEO friendly"],
                "common_issues": ["security vulnerabilities", "performance", "maintenance"],
                "upgrade_opportunities": ["custom themes", "performance optimization", "security hardening"]
            },
            "shopify": {
                "market_share": 10.3,
                "strengths": ["e-commerce focused", "easy setup", "payment integration"],
                "common_issues": ["customization limitations", "transaction fees", "SEO limitations"],
                "upgrade_opportunities": ["custom apps", "advanced integrations", "performance optimization"]
            },
            "drupal": {
                "market_share": 2.1,
                "strengths": ["enterprise features", "security", "scalability"],
                "common_issues": ["complexity", "maintenance costs", "learning curve"],
                "upgrade_opportunities": ["module development", "migration assistance", "training"]
            }
        },
        "hosting_providers": {
            "shared_hosting": {
                "indicators": ["cpanel", "hostgator", "bluehost"],
                "typical_issues": ["performance limitations", "security concerns", "scalability"],
                "upgrade_path": "VPS or cloud hosting migration"
            },
            "cloud_hosting": {
                "indicators": ["aws", "azure", "google cloud", "cloudflare"],
                "typical_issues": ["cost optimization", "configuration complexity", "monitoring"],
                "upgrade_path": "managed services, optimization consulting"
            }
        },
        "frameworks": {
            "react": {
                "version_indicators": ["react 16", "react 17", "react 18"],
                "common_issues": ["performance optimization", "SEO challenges", "bundle size"],
                "opportunities": ["server-side rendering", "performance tuning", "modern patterns"]
            },
            "angular": {
                "version_indicators": ["angularjs", "angular 2+"],
                "common_issues": ["migration needs", "performance", "complexity"],
                "opportunities": ["framework migration", "performance optimization", "modernization"]
            }
        }
    }
    
    # 3. Industry Benchmarks
    industry_benchmarks = {
        "performance_benchmarks": {
            "page_load_time": {
                "excellent": "< 2 seconds",
                "good": "2-3 seconds", 
                "average": "3-5 seconds",
                "poor": "> 5 seconds"
            },
            "mobile_score": {
                "excellent": "> 90",
                "good": "80-90",
                "average": "60-80", 
                "poor": "< 60"
            }
        },
        "industry_standards": {
            "healthcare": {
                "required_compliance": ["HIPAA", "SOC 2"],
                "security_requirements": ["SSL", "data encryption", "access controls"],
                "typical_budget": "$50,000 - $200,000"
            },
            "finance": {
                "required_compliance": ["PCI DSS", "SOX", "GDPR"],
                "security_requirements": ["multi-factor auth", "encryption", "audit trails"],
                "typical_budget": "$75,000 - $300,000"
            }
        }
    }
    
    # 4. Proposal Templates
    proposal_templates = {
        "web_development": {
            "executive_summary": "Transform your digital presence with a modern, responsive website that drives conversions and enhances user experience.",
            "key_deliverables": [
                "Responsive web design",
                "Performance optimization",
                "SEO implementation",
                "Content management system",
                "Analytics setup"
            ],
            "timeline": "6-8 weeks",
            "investment_range": "$15,000 - $50,000"
        },
        "cloud_migration": {
            "executive_summary": "Modernize your infrastructure with secure, scalable cloud solutions that reduce costs and improve reliability.",
            "key_deliverables": [
                "Infrastructure assessment",
                "Migration strategy",
                "Cloud architecture design",
                "Data migration",
                "Monitoring setup"
            ],
            "timeline": "8-12 weeks",
            "investment_range": "$25,000 - $75,000"
        }
    }
    
    # 5. Email Templates
    email_templates = {
        "cold_outreach": {
            "web_development": {
                "subject": "Quick question about {company_name}'s website",
                "body": "Hi {contact_name},\n\nI came across {company_name} and noticed some opportunities to improve your website's {identified_issue}.\n\nWe've helped similar {industry} companies achieve:\n• {benefit_1}\n• {benefit_2}\n• {benefit_3}\n\nWould you be open to a brief call to discuss how we could help {company_name}?\n\nBest regards,\n{sender_name}"
            }
        },
        "follow_up": {
            "general": {
                "subject": "Following up on {company_name}",
                "body": "Hi {contact_name},\n\nI wanted to follow up on my previous message about {topic}.\n\nBased on our analysis of {company_name}, we identified specific opportunities that could deliver significant value.\n\nWould you have 10 minutes this week for a quick discussion?\n\nBest,\n{sender_name}"
            }
        }
    }
    
    # Save all files
    files_to_create = [
        (kb_dir / "it_services_knowledge.json", it_services_data),
        (kb_dir / "technology_database.json", technology_database),
        (kb_dir / "industry_benchmark.json", industry_benchmarks),
        (kb_dir / "proposal_templates.json", proposal_templates),
        (kb_dir / "email_templates.json", email_templates)
    ]
    
    created_files = []
    for filepath, data in files_to_create:
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            created_files.append(filepath.name)
            print(f"✅ Created: {filepath.name}")
        except Exception as e:
            print(f"❌ Failed to create {filepath.name}: {str(e)}")
    
    print(f"\n🎉 Knowledge base setup complete!")
    print(f"📁 Created {len(created_files)} knowledge base files")
    print(f"📍 Location: {kb_dir}")
    
    return created_files
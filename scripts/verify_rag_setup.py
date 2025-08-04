"""Verify RAG system is working properly"""
import sys
from pathlib import Path
import asyncio

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from rag.knowledge_base import KnowledgeBase
from rag.retrieval import RetrievalService
from app.config import settings

async def verify_rag_setup():
    """Comprehensive RAG system verification"""
    
    print("🔍 Verifying RAG Setup...")
    print("=" * 50)
    
    # 1. Check knowledge base files
    kb_dir = Path(settings.KNOWLEDGE_BASE_DIR)
    required_files = [
        "it_services_knowledge.json",
        "technology_database.json", 
        "industry_benchmark.json",
        "proposal_templates.json",
        "email_templates.json"
    ]
    
    print("📁 Checking knowledge base files:")
    missing_files = []
    for filename in required_files:
        filepath = kb_dir / filename
        if filepath.exists():
            print(f"   ✅ {filename}")
        else:
            print(f"   ❌ {filename} - MISSING!")
            missing_files.append(filename)
    
    if missing_files:
        print(f"\n⚠️  Missing files: {missing_files}")
        print("💡 Run: python scripts/setup_knowledge_base.py")
        return False
    
    # 2. Test knowledge base loading
    print("\n🧠 Testing Knowledge Base:")
    try:
        kb = KnowledgeBase()
        stats = kb.get_knowledge_stats()
        print(f"   ✅ Loaded {stats['total_items']} knowledge items")
        print(f"   ✅ Categories: {list(stats['categories'].keys())}")
        print(f"   ✅ Embeddings: {stats['has_embeddings']}")
        print(f"   ✅ Embedding dimensions: {stats['embedding_dimensions']}")
    except Exception as e:
        print(f"   ❌ Knowledge base loading failed: {str(e)}")
        return False
    
    # 3. Test retrieval
    print("\n🔎 Testing Retrieval:")
    try:
        test_queries = [
            "website is slow and not mobile friendly",
            "need cloud migration for growing business", 
            "security concerns and compliance issues"
        ]
        
        for query in test_queries:
            context = await kb.get_relevant_context(query, top_k=2)
            print(f"   Query: '{query}'")
            print(f"   📊 Found {len(context)} relevant contexts")
            if context:
                best_match = context[0]
                print(f"   🎯 Best match: {best_match['category']} (similarity: {best_match['similarity']:.3f})")
            print()
            
    except Exception as e:
        print(f"   ❌ Retrieval testing failed: {str(e)}")
        return False
    
    # 4. Test retrieval service
    print("🔄 Testing Retrieval Service:")
    try:
        retrieval_service = RetrievalService()
        context = await retrieval_service.retrieve_context("wordpress website needs security improvements")
        print(f"   ✅ Retrieved context types: {list(context.keys())}")
    except Exception as e:
        print(f"   ❌ Retrieval service failed: {str(e)}")
        return False
    
    print("\n🎉 RAG System Verification Complete!")
    print("✅ All components working properly")
    return True

if __name__ == "__main__":
    asyncio.run(verify_rag_setup())
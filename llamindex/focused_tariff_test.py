import os
import json
from dotenv import load_dotenv
load_dotenv()

from llama_index.core import Settings
from custom_llm import llm_retrieval
from embedding_model import embed_model
from storage_manager import StorageManager
from tool_cache import ToolCache

# Update Global LLM and Embedding Model
Settings.llm = llm_retrieval
Settings.embed_model = embed_model

def focused_tariff_test():
    """Test with only tariff-related documents."""
    
    print("🎯 FOCUSED TARIFF DOCUMENT TEST")
    print("=" * 50)
    
    # Initialize storage manager and tool cache
    storage_manager = StorageManager(base_dir="./regulatory_storage")
    tool_cache = ToolCache(storage_manager, cache_dir="./tool_cache")
    
    # Get all documents
    all_documents = storage_manager.list_documents()
    
    # Filter to only tariff-related documents
    tariff_keywords = ['tariff', 're', 'renewable', 'merc']
    tariff_docs = []
    
    for doc in all_documents:
        doc_lower = doc.lower()
        if any(keyword in doc_lower for keyword in tariff_keywords):
            tariff_docs.append(doc)
    
    print(f"📋 Found {len(tariff_docs)} tariff-related documents:")
    for doc in tariff_docs[:10]:  # Show first 10
        print(f"  - {doc}")
    if len(tariff_docs) > 10:
        print(f"  ... and {len(tariff_docs) - 10} more")
    
    # Load tools for tariff documents only
    document_tools = {}
    for doc_name in tariff_docs:
        try:
            doc_tools = tool_cache.get_tools_for_document(doc_name)
            document_tools[doc_name] = doc_tools
            print(f"✅ Loaded {doc_tools['node_count']} nodes for {doc_name}")
        except Exception as e:
            print(f"❌ Error loading {doc_name}: {e}")
    
    if not document_tools:
        print("No tariff documents loaded!")
        return
    
    # Collect all tools
    all_tools = []
    for doc_name, doc_info in document_tools.items():
        all_tools.extend([doc_info['vector_tool'], doc_info['summary_tool']])
    
    print(f"\n📦 Total tools loaded: {len(all_tools)}")
    
    # Test simple queries
    simple_queries = [
        "tariff",
        "solar", 
        "wind",
        "renewable energy"
    ]
    
    print(f"\n🔍 Testing {len(simple_queries)} simple queries on tariff documents...")
    print("=" * 60)
    
    for i, query in enumerate(simple_queries, 1):
        print(f"\nQuery {i}: '{query}'")
        print("-" * 40)
        
        try:
            response = llm_retrieval.predict_and_call(
                all_tools,
                query,
                verbose=True
            )
            
            print(f"\n✅ Response received!")
            print(f"Response length: {len(str(response))}")
            print(f"Response preview: {str(response)[:300]}...")
            
        except Exception as e:
            print(f"❌ Error during query: {e}")
        
        print()
    
    print("🎯 FOCUSED TEST SUMMARY:")
    print("✅ Testing only tariff-related documents")
    print("✅ Using simple, single-word queries")
    print("✅ Should demonstrate vector search working")

if __name__ == "__main__":
    focused_tariff_test() 
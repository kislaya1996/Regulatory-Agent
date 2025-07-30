import os
from storage_manager import StorageManager
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import TextNode
from llama_index.core import Settings
from custom_llm import llm_indexing
from embedding_model import embed_model

# Set up global settings
Settings.llm = llm_indexing
Settings.embed_model = embed_model

def test_storage_fix():
    """Test the storage fix."""
    
    print("=== Testing Storage Fix ===\n")
    
    # Initialize storage manager
    storage_manager = StorageManager(base_dir="./simple_test_storage")
    
    # Create some test nodes
    test_nodes = [
        TextNode(text="This is a test document about tariff rates. The rates are 5.5% for residential customers."),
        TextNode(text="The regulatory order mentions that commercial customers pay 7.2% tariff rates."),
    ]
    
    document_name = "simple_test"
    
    print(f"1. Creating test nodes for {document_name}")
    print(f"   - Created {len(test_nodes)} test nodes")
    
    # Save the nodes
    storage_manager.save_nodes(test_nodes, document_name)
    print("   - Saved nodes to storage")
    
    # Create vector index
    print("\n2. Creating vector index...")
    vector_index = VectorStoreIndex(test_nodes)
    print("   - Vector index created")
    
    # Save vector index to ChromaDB
    print("\n3. Saving vector index to ChromaDB...")
    storage_manager.save_vector_index(vector_index, document_name, use_chroma=True)
    print("   - Vector index saved to ChromaDB")
    
    # Load vector index from ChromaDB
    print("\n4. Loading vector index from ChromaDB...")
    loaded_index = storage_manager.load_vector_index(document_name, use_chroma=True)
    
    if loaded_index is None:
        print("   ❌ Failed to load vector index from ChromaDB")
        return False
    else:
        print("   ✅ Successfully loaded vector index from ChromaDB")
        
        # Test a simple query
        print("\n5. Testing query on loaded index...")
        query_engine = loaded_index.as_query_engine(similarity_top_k=2)
        response = query_engine.query("What are the tariff rates?")
        print(f"   Query: 'What are the tariff rates?'")
        print(f"   Response: {str(response)}")
        
        if str(response).strip():
            print("   ✅ Query returned a response")
            return True
        else:
            print("   ❌ Query returned empty response")
            return False

if __name__ == "__main__":
    success = test_storage_fix()
    if success:
        print("\n🎉 Storage fix test PASSED!")
    else:
        print("\n💥 Storage fix test FAILED!") 
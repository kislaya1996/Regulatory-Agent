import os
import json
from storage_manager import StorageManager
from llama_index.core import VectorStoreIndex, SummaryIndex
from llama_index.core.schema import TextNode
from llama_index.core import Settings
from custom_llm import llm_indexing, llm_retrieval
from embedding_model import embed_model
from vector_tool_factory import create_vector_query_tool
from summary_tool_factory import create_summary_tool

# Set up global settings
Settings.llm = llm_indexing
Settings.embed_model = embed_model

def test_storage_issue():
    """Test the storage issue with empty responses on subsequent runs."""
    
    print("=== Testing Storage Issue ===\n")
    
    # Initialize storage manager
    storage_manager = StorageManager(base_dir="./test_storage")
    
    # Create some test nodes
    test_nodes = [
        TextNode(text="This is a test document about tariff rates. The rates are 5.5% for residential customers."),
        TextNode(text="The regulatory order mentions that commercial customers pay 7.2% tariff rates."),
        TextNode(text="Industrial customers have different tariff structures based on their consumption patterns."),
        TextNode(text="The order was issued on January 15, 2024 and is effective immediately."),
        TextNode(text="Cross-subsidy charges are calculated at 0.5% for all customer categories.")
    ]
    
    document_name = "test_document"
    
    print(f"1. Creating test nodes for {document_name}")
    print(f"   - Created {len(test_nodes)} test nodes")
    
    # Save the nodes
    storage_manager.save_nodes(test_nodes, document_name)
    print("   - Saved nodes to storage")
    
    # Create tools with persistence
    print("\n2. Creating vector query tool...")
    vector_query_tool = create_vector_query_tool(
        nodes=test_nodes,
        document_name=document_name,
        storage_manager=storage_manager,
        use_chroma=True
    )
    print("   - Vector query tool created")
    
    print("\n3. Creating summary tool...")
    summary_tool = create_summary_tool(
        nodes=test_nodes,
        document_name=document_name,
        storage_manager=storage_manager
    )
    print("   - Summary tool created")
    
    # Switch to retrieval LLM
    Settings.llm = llm_retrieval
    
    print("\n4. Testing tool calls...")
    
    # Test query 1
    print("\n   Query 1: 'What are the tariff rates mentioned?'")
    response_1 = llm_retrieval.predict_and_call(
        [vector_query_tool, summary_tool],
        "What are the tariff rates mentioned?",
        verbose=True
    )
    print(f"   Response 1: {str(response_1)}")
    
    # Test query 2
    print("\n   Query 2: 'Provide a summary of this document'")
    response_2 = llm_retrieval.predict_and_call(
        [vector_query_tool, summary_tool],
        "Provide a summary of this document",
        verbose=True
    )
    print(f"   Response 2: {str(response_2)}")
    
    print("\n5. Now testing with existing storage...")
    
    # Load existing nodes
    existing_nodes = storage_manager.load_nodes(document_name)
    print(f"   - Loaded {len(existing_nodes)} existing nodes")
    
    # Create tools again with existing nodes
    print("\n6. Creating tools with existing nodes...")
    vector_query_tool_2 = create_vector_query_tool(
        nodes=existing_nodes,
        document_name=document_name,
        storage_manager=storage_manager,
        use_chroma=True
    )
    print("   - Vector query tool created (with existing nodes)")
    
    summary_tool_2 = create_summary_tool(
        nodes=existing_nodes,
        document_name=document_name,
        storage_manager=storage_manager
    )
    print("   - Summary tool created (with existing nodes)")
    
    print("\n7. Testing tool calls with existing storage...")
    
    # Test query 3 (should work the same as query 1)
    print("\n   Query 3: 'What are the tariff rates mentioned?' (with existing storage)")
    response_3 = llm_retrieval.predict_and_call(
        [vector_query_tool_2, summary_tool_2],
        "What are the tariff rates mentioned?",
        verbose=True
    )
    print(f"   Response 3: {str(response_3)}")
    
    # Test query 4 (should work the same as query 2)
    print("\n   Query 4: 'Provide a summary of this document' (with existing storage)")
    response_4 = llm_retrieval.predict_and_call(
        [vector_query_tool_2, summary_tool_2],
        "Provide a summary of this document",
        verbose=True
    )
    print(f"   Response 4: {str(response_4)}")
    
    print("\n=== Test Complete ===")
    
    # Check if responses are empty
    if not str(response_3).strip() or str(response_3) == "None":
        print("\n❌ ISSUE FOUND: Response 3 is empty!")
        return False
    elif not str(response_4).strip() or str(response_4) == "None":
        print("\n❌ ISSUE FOUND: Response 4 is empty!")
        return False
    else:
        print("\n✅ No empty responses detected")
        return True

if __name__ == "__main__":
    test_storage_issue() 
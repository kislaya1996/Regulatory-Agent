import os
import json
from storage_manager import StorageManager
from custom_llm import llm_retrieval
from vector_tool_factory import create_vector_query_tool
from summary_tool_factory import create_summary_tool

def test_simple_queries():
    """Test the core query functionality with existing processed nodes."""
    
    # Initialize storage manager
    storage_manager = StorageManager(base_dir="./regulatory_storage")
    
    # Document name
    document_name = "MSEDCL-MYT-Order_Case_no_217-of-2024"
    
    # Load existing nodes
    print(f"Loading existing nodes for {document_name}...")
    nodes = storage_manager.load_nodes(document_name)
    
    if not nodes:
        print("No existing nodes found. Please run the full processing script first.")
        return
    
    print(f"Loaded {len(nodes)} nodes")
    
    # Validate nodes
    valid_nodes = []
    for node in nodes:
        content = node.get_content()
        if len(content) > 50 and not content.startswith('%PDF') and not ' 0 R ' in content[:100]:
            valid_nodes.append(node)
    
    if len(valid_nodes) == 0:
        print("No valid nodes found. The document needs to be reprocessed.")
        return
    
    print(f"Using {len(valid_nodes)} valid nodes")
    
    # Create tools
    print("Creating vector query tool...")
    vector_query_tool = create_vector_query_tool(
        nodes=valid_nodes,
        document_name=document_name,
        storage_manager=storage_manager,
        use_chroma=True
    )
    
    print("Creating summary tool...")
    summary_tool = create_summary_tool(
        nodes=valid_nodes,
        document_name=document_name,
        storage_manager=storage_manager,
        use_chroma=True
    )
    
    # Test queries
    print("\n--- Testing Queries ---")
    
    # Test 1: Simple search query
    print("\nQuery 1: What are the tariff rates mentioned in this order?")
    try:
        response_1 = llm_retrieval.predict_and_call(
            [vector_query_tool, summary_tool],
            "What are the tariff rates mentioned in this order?",
            verbose=True
        )
        print(f"Response 1: {str(response_1)}")
    except Exception as e:
        print(f"Error in Query 1: {e}")
    
    # Test 2: Summary query
    print("\nQuery 2: Provide a brief summary of this regulatory order")
    try:
        response_2 = llm_retrieval.predict_and_call(
            [vector_query_tool, summary_tool],
            "Provide a brief summary of this regulatory order",
            verbose=True
        )
        print(f"Response 2: {str(response_2)}")
    except Exception as e:
        print(f"Error in Query 2: {e}")
    
    # Test 3: Specific data query
    print("\nQuery 3: What are the Fixed Charges for HT consumers?")
    try:
        response_3 = llm_retrieval.predict_and_call(
            [vector_query_tool, summary_tool],
            "What are the Fixed Charges for HT consumers?",
            verbose=True
        )
        print(f"Response 3: {str(response_3)}")
    except Exception as e:
        print(f"Error in Query 3: {e}")

if __name__ == "__main__":
    test_simple_queries() 
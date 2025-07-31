import os
import pickle
from pathlib import Path
from storage_manager import StorageManager

def debug_nodes_content():
    """Debug the content of stored nodes to identify encoding issues."""
    
    # Initialize storage manager
    storage_manager = StorageManager(base_dir="./regulatory_storage")
    
    # Document name from your test
    document_name = "MSEDCL-MYT-Order_Case_no_217-of-2024"
    
    # Load nodes
    nodes = storage_manager.load_nodes(document_name)
    
    if not nodes:
        print("No nodes found!")
        return
    
    print(f"Found {len(nodes)} nodes")
    
    # Examine first few nodes
    for i, node in enumerate(nodes[:5]):
        print(f"\n--- Node {i+1} ---")
        print(f"Node ID: {node.node_id}")
        print(f"Node type: {type(node)}")
        
        # Get content
        content = node.get_content()
        print(f"Content length: {len(content)}")
        print(f"Content preview (first 200 chars): {repr(content[:200])}")
        
        # Check for encoding issues
        try:
            content.encode('utf-8')
            print("✓ Content is valid UTF-8")
        except UnicodeEncodeError as e:
            print(f"✗ UTF-8 encoding error: {e}")
        
        # Check for common corruption patterns
        if '\x00' in content:
            print("✗ Contains null bytes (corruption indicator)")
        
        if content.count('') > 10:
            print("✗ Contains many replacement characters (encoding issue)")
        
        # Show metadata
        print(f"Metadata: {node.metadata}")
        
        print("-" * 50)

if __name__ == "__main__":
    debug_nodes_content() 
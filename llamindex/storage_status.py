#!/usr/bin/env python3
"""
Utility script to check the status of stored documents and indexes.
This script provides a quick overview of what's been processed and stored.
"""

import json
import os
from pathlib import Path
from storage_manager import StorageManager

def check_storage_status(base_dir: str = "./regulatory_storage"):
    """Check the status of all stored documents."""
    
    print("=== Storage Status Report ===\n")
    
    # Check if storage directory exists
    if not os.path.exists(base_dir):
        print(f"❌ Storage directory not found: {base_dir}")
        print("No documents have been processed yet.")
        return
    
    storage_manager = StorageManager(base_dir=base_dir)
    
    # List all documents
    documents = storage_manager.list_documents()
    
    if not documents:
        print("📭 No documents found in storage.")
        return
    
    print(f"📚 Found {len(documents)} processed document(s):\n")
    
    total_nodes = 0
    total_size = 0
    
    for i, doc_name in enumerate(documents, 1):
        print(f"{i}. {doc_name}")
        
        # Get metadata
        metadata = storage_manager.get_document_metadata(doc_name)
        
        # Check nodes
        if metadata.get('nodes', {}).get('exists', False):
            nodes_file = metadata['nodes']['file_path']
            if os.path.exists(nodes_file):
                size = os.path.getsize(nodes_file) / (1024 * 1024)  # MB
                total_size += size
                print(f"   📄 Nodes: {size:.2f} MB")
        
        # Check vector index
        if 'vector_index' in metadata:
            vector_info = metadata['vector_index']
            node_count = vector_info.get('node_count', 'Unknown')
            storage_type = vector_info.get('storage_type', 'Unknown')
            print(f"   🔍 Vector Index: {node_count} nodes ({storage_type})")
            total_nodes += node_count if isinstance(node_count, int) else 0
        
        # Check summary index
        if 'summary_index' in metadata:
            summary_info = metadata['summary_index']
            node_count = summary_info.get('node_count', 'Unknown')
            print(f"   📝 Summary Index: {node_count} nodes")
        
        print()
    
    # Summary
    print("=== Summary ===")
    print(f"Total documents: {len(documents)}")
    print(f"Total nodes: {total_nodes}")
    print(f"Total storage size: {total_size:.2f} MB")
    
    # Storage directory info
    storage_path = Path(base_dir)
    if storage_path.exists():
        total_dir_size = sum(f.stat().st_size for f in storage_path.rglob('*') if f.is_file())
        total_dir_size_mb = total_dir_size / (1024 * 1024)
        print(f"Total directory size: {total_dir_size_mb:.2f} MB")

def check_storage_health(base_dir: str = "./regulatory_storage"):
    """Check the health of stored data."""
    
    print("\n=== Storage Health Check ===\n")
    
    if not os.path.exists(base_dir):
        print("❌ Storage directory not found")
        return
    
    storage_manager = StorageManager(base_dir=base_dir)
    documents = storage_manager.list_documents()
    
    if not documents:
        print("✅ No documents to check")
        return
    
    issues_found = []
    
    for doc_name in documents:
        print(f"Checking {doc_name}...")
        
        # Check nodes
        nodes = storage_manager.load_nodes(doc_name)
        if nodes is None:
            issues_found.append(f"❌ {doc_name}: Cannot load nodes")
        else:
            print(f"   ✅ Nodes: {len(nodes)} loaded successfully")
        
        # Check vector index
        vector_index = storage_manager.load_vector_index(doc_name, use_chroma=True)
        if vector_index is None:
            # Try file-based storage
            vector_index = storage_manager.load_vector_index(doc_name, use_chroma=False)
            if vector_index is None:
                issues_found.append(f"❌ {doc_name}: Cannot load vector index")
            else:
                print(f"   ✅ Vector Index: Loaded from file storage")
        else:
            print(f"   ✅ Vector Index: Loaded from ChromaDB")
        
        # Check summary index
        summary_index = storage_manager.load_summary_index(doc_name)
        if summary_index is None:
            issues_found.append(f"❌ {doc_name}: Cannot load summary index")
        else:
            print(f"   ✅ Summary Index: Loaded successfully")
        
        print()
    
    if issues_found:
        print("❌ Issues found:")
        for issue in issues_found:
            print(f"   {issue}")
    else:
        print("✅ All documents are healthy!")

def main():
    """Main function to run storage status checks."""
    
    # Check status
    check_storage_status()
    
    # Check health
    check_storage_health()
    
    print("\n=== Storage Status Complete ===")

if __name__ == "__main__":
    main() 
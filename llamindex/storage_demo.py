#!/usr/bin/env python3
"""
Demo script showcasing the Storage Manager functionality for regulatory documents.
This script demonstrates how to use the storage manager to save, load, and manage
nodes and indexes with persistence.
"""

import os
import json
from storage_manager import StorageManager
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import TitleExtractor
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from llama_index.core import VectorStoreIndex, SummaryIndex
from llama_index.core import Settings
from custom_llm import llm_indexing
from embedding_model import embed_model

# Set up global settings
Settings.llm = llm_indexing
Settings.embed_model = embed_model

def demo_storage_manager():
    """Demonstrate the storage manager functionality."""
    
    print("=== Storage Manager Demo ===\n")
    
    # Initialize storage manager
    storage_manager = StorageManager(base_dir="./demo_storage")
    
    # Example document path (you can change this to your actual document)
    filename = "../merc_test_files/orders/MSEDCL-MYT-Order_Case_no_217-of-2024.pdf"
    
    if not os.path.exists(filename):
        print(f"Document not found: {filename}")
        print("Please update the filename variable to point to an existing PDF file.")
        return
    
    document_name = os.path.splitext(os.path.basename(filename))[0]
    print(f"Processing document: {document_name}")
    
    # Step 1: Check for existing nodes
    print("\n1. Checking for existing processed nodes...")
    existing_nodes = storage_manager.load_nodes(document_name)
    
    if existing_nodes:
        print(f"✓ Found {len(existing_nodes)} existing nodes")
        nodes = existing_nodes
    else:
        print("✗ No existing nodes found, processing document...")
        
        # Process the document
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(chunk_size=1024, chunk_overlap=50),
                TitleExtractor(nodes=2),
            ],
            cache=IngestionCache(
                cache_dir="./cache",
                collection_name="demo_docs"
            )
        )
        
        documents = SimpleDirectoryReader(input_files=[filename]).load_data()
        nodes = pipeline.run(documents=documents)
        
        # Save the nodes
        storage_manager.save_nodes(nodes, document_name)
        print(f"✓ Saved {len(nodes)} nodes")
    
    # Step 2: Create and save vector index
    print("\n2. Creating vector index...")
    vector_index = VectorStoreIndex(nodes)
    storage_manager.save_vector_index(vector_index, document_name, use_chroma=True)
    print("✓ Vector index saved with ChromaDB persistence")
    
    # Step 3: Create and save summary index
    print("\n3. Creating summary index...")
    summary_index = SummaryIndex(nodes)
    storage_manager.save_summary_index(summary_index, document_name)
    print("✓ Summary index saved")
    
    # Step 4: Demonstrate loading indexes
    print("\n4. Demonstrating index loading...")
    
    # Load vector index
    loaded_vector_index = storage_manager.load_vector_index(document_name, use_chroma=True)
    if loaded_vector_index:
        print("✓ Vector index loaded successfully")
    
    # Load summary index
    loaded_summary_index = storage_manager.load_summary_index(document_name)
    if loaded_summary_index:
        print("✓ Summary index loaded successfully")
    
    # Step 5: Show metadata
    print("\n5. Document metadata:")
    metadata = storage_manager.get_document_metadata(document_name)
    print(json.dumps(metadata, indent=2))
    
    # Step 6: List all documents
    print("\n6. All stored documents:")
    all_docs = storage_manager.list_documents()
    for doc in all_docs:
        print(f"  - {doc}")
    
    print("\n=== Demo completed successfully! ===")

def demo_storage_operations():
    """Demonstrate various storage operations."""
    
    print("\n=== Storage Operations Demo ===\n")
    
    storage_manager = StorageManager(base_dir="./demo_storage")
    
    # List all documents
    print("1. Current stored documents:")
    documents = storage_manager.list_documents()
    for doc in documents:
        print(f"  - {doc}")
    
    if documents:
        # Show metadata for first document
        first_doc = documents[0]
        print(f"\n2. Metadata for '{first_doc}':")
        metadata = storage_manager.get_document_metadata(first_doc)
        print(json.dumps(metadata, indent=2))
        
        # Demonstrate deletion (commented out for safety)
        print(f"\n3. To delete '{first_doc}', uncomment the following line:")
        print(f"   storage_manager.delete_document('{first_doc}')")
        # storage_manager.delete_document(first_doc)
    
    print("\n=== Operations demo completed! ===")

if __name__ == "__main__":
    try:
        demo_storage_manager()
        demo_storage_operations()
    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc() 
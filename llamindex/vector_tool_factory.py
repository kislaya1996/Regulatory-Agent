import os
from typing import List, Optional
from llama_index.core.vector_stores import MetadataFilters, FilterCondition
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import BaseNode
from llama_index.core.tools import FunctionTool
from llama_index.core.storage import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
from llama_index.core import Settings # Make sure Settings is imported for global configs

from storage_manager import StorageManager
# from custom_llm import llm_retrieval # Assuming you're setting LLM globally or passing to query engine

# Ensure your LLM and Embedding Model are set up globally or passed explicitly
# Example:
# Settings.llm = YourCustomLLMInstance
# Settings.embed_model = YourCustomEmbeddingModelInstance

def create_vector_query_tool(
    nodes: List[BaseNode],
    document_name: str,
    storage_manager: Optional[StorageManager] = None,
    use_chroma: bool = True
) -> FunctionTool:
    """
    Create a vector query tool with optional persistence.
    
    Args:
        nodes: List of nodes to create the index from
        document_name: Name identifier for the document
        storage_manager: Optional storage manager for persistence
        use_chroma: Whether to use ChromaDB for storage
    """
    
    if storage_manager is None:
        raise ValueError("StorageManager must be provided for persistence.")

    print(f"\n--- Setting up Vector Index Tool for {document_name} ---")

    # Define paths for ChromaDB collection and LlamaIndex's internal storage for vector index
    chroma_collection_name = f"{document_name}_collection"
    # This path is for LlamaIndex's internal components (docstore, index_store)
    vector_index_persist_dir = os.path.join(storage_manager.vector_indexes_dir, document_name)

    # Try to load existing index first
    vector_index = None
    if storage_manager:
        print(f"Attempting to load existing vector index for {document_name} from {vector_index_persist_dir}...")
        try:
            vector_index = storage_manager.load_vector_index(document_name, use_chroma=use_chroma)
        except Exception as e:
            print(f"Error loading existing vector index: {e}")
            print("Will create new vector index from nodes...")
            vector_index = None
    
    # If no existing index, create new one
    if vector_index is None:
        print(f"Creating new vector index for {document_name}")
        os.makedirs(vector_index_persist_dir, exist_ok=True) 
        
        if use_chroma: # Use ChromaDB for vector storage
            # Initialize ChromaDB client and collection for this specific vector index
            chroma_client = chromadb.PersistentClient(path=str(storage_manager.chroma_dir))
            
            # Use get_or_create_collection for robustness
            collection = chroma_client.get_or_create_collection(name=chroma_collection_name)
            print(f"Using/Created ChromaDB collection: {collection.name}")

            
            # Create ChromaVectorStore
            vector_store = ChromaVectorStore(chroma_collection=collection)
            
            # Create StorageContext without persist_dir first to avoid loading existing components
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store
            )
            
            # Create VectorStoreIndex with persistent storage
            vector_index = VectorStoreIndex(
                nodes,
                storage_context=storage_context,
                show_progress=True # Optional: see progress
            )
            
            # Now persist the index to the specified directory
            vector_index.storage_context.persist(persist_dir=vector_index_persist_dir)
            
            # Save the index metadata (ChromaDB handles its own data persistence)
            storage_manager.save_vector_index(vector_index, document_name, use_chroma=True)
            print(f"Successfully created and persisted new vector index for {document_name}")

        else: # Use file-based storage (SimpleVectorStore implicitly)
            # Create a dedicated directory for file-based persistence for this index
            file_index_dir = os.path.join(storage_manager.vector_indexes_dir, f"{document_name}_file_based")
            os.makedirs(file_index_dir, exist_ok=True) # Ensure directory exists

            # Create StorageContext without persist_dir first to avoid loading existing components
            storage_context = StorageContext.from_defaults()
            vector_index = VectorStoreIndex(
                nodes,
                storage_context=storage_context,
                show_progress=True # Optional: see progress
            )
            
            # Now persist the index to the specified directory
            vector_index.storage_context.persist(persist_dir=file_index_dir)
            
            # Save the index (LlamaIndex's persist method will handle SimpleVectorStore and other components)
            storage_manager.save_vector_index(vector_index, document_name, use_chroma=False)
            print(f"Successfully created and persisted new file-based vector index for {document_name}")

    else:
        print(f"Successfully loaded existing vector index for {document_name}")

    def vector_query(
        query: str,
        page_numbers: List[str],
    ) -> str:
        """Perform a vector search over the regulatory document index.

        query (str): the string query to be embedded.
        page_numbers (List[str]): Filter by set of pages. Leave BLANK if we want to perform a vector search
            over all pages. Otherwise, filter by the set of specified pages.

        """
        try:
            if not page_numbers or page_numbers == ["all"]:
                # No page filter - search all pages
                query_engine = vector_index.as_query_engine(
                    similarity_top_k=3,
                    # llm=llm_retrieval # Pass LLM if not set globally
                )
            else:
                metadata_filters = MetadataFilters.from_dicts(
                    [{"key": "page_label", "value": p} for p in page_numbers],
                    condition=FilterCondition.OR
                )
                query_engine = vector_index.as_query_engine(
                    similarity_top_k=3,
                    filters=metadata_filters,
                    # llm=llm_retrieval # Pass LLM if not set globally
                )
            
            response = query_engine.query(query)
            response_text = str(response)
            
            # Validate response content
            if len(response_text) < 10:
                return "No relevant information found for your query. Please try rephrasing your question."
            
            # Check for corrupted content indicators
            if response_text.startswith('%PDF') or ' 0 R ' in response_text[:200]:
                return "Error: Retrieved content appears to be corrupted. Please try a different query or contact support."
            
            return response_text
            
        except Exception as e:
            error_msg = str(e)
            if "Input is too long" in error_msg:
                return "The query returned too much content. Please try a more specific question."
            elif "ValidationException" in error_msg:
                return "Error: The model could not process the request. Please try a simpler query."
            else:
                return f"Error performing vector search: {error_msg}"

    return FunctionTool.from_defaults(
        name="regulatory_search_tool",
        fn=vector_query,
        description=(
            "Use this tool when you need to find specific information, details, or facts within the regulatory order. "
            "This tool performs semantic search to find relevant content based on your query. "
            "Use this for questions like 'What are the tariff rates', 'Find information about X', 'What does the order say about Y', "
            "or when you're looking for specific data, numbers, dates, or detailed information within the document. "
            "This is NOT for general summaries or overviews - use the summary tool for those."
        )
    )
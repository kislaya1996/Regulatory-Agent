from typing import List, Optional
from llama_index.core.vector_stores import MetadataFilters, FilterCondition
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import BaseNode
from llama_index.core.tools import FunctionTool
from storage_manager import StorageManager


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
    
    # Try to load existing index first
    vector_index = None
    if storage_manager:
        vector_index = storage_manager.load_vector_index(document_name, use_chroma=use_chroma)
    
    # If no existing index, create new one
    if vector_index is None:
        print(f"Creating new vector index for {document_name}")
        vector_index = VectorStoreIndex(nodes)
        
        # Save the index if storage manager is provided
        if storage_manager:
            storage_manager.save_vector_index(vector_index, document_name, use_chroma=use_chroma)

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
                query_engine = vector_index.as_query_engine(similarity_top_k=3)
            else:
                metadata_dicts = [
                    {"key": "page_label", "value": p} for p in page_numbers
                ]
                query_engine = vector_index.as_query_engine(
                    similarity_top_k=3,
                    filters=MetadataFilters.from_dicts(
                        metadata_dicts,
                        condition=FilterCondition.OR
                    )
                )
            
            response = query_engine.query(query)
            return str(response)
        except Exception as e:
            return f"Error performing vector search: {str(e)}"

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
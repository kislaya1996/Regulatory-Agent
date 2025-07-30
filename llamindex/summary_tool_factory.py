from llama_index.core.tools import FunctionTool, QueryEngineTool
from llama_index.core.schema import BaseNode
from llama_index.core import VectorStoreIndex
from typing import List, Optional
from storage_manager import StorageManager
from custom_llm import llm_retrieval

def create_summary_tool(
    nodes: List[BaseNode],
    document_name: str,
    storage_manager: Optional[StorageManager] = None
) -> FunctionTool:
    """
    Create a summary tool with optional persistence.
    
    Args:
        nodes: List of nodes to create the summary index from
        document_name: Name identifier for the document
        storage_manager: Optional storage manager for persistence
    """
    print(f"\n--- Setting up Summary Index Tool for {document_name} ---")
    
    # Try to load existing index first
    vector_index = None
    if storage_manager:
        vector_index = storage_manager.load_vector_index(document_name, use_chroma=False)
    
    # If no existing index, create new one
    if vector_index is None:
        print(f"Creating new vector index for summary tool for {document_name}")
        vector_index = VectorStoreIndex(nodes)
        
        # Save the index if storage manager is provided
        if storage_manager:
            storage_manager.save_vector_index(vector_index, document_name, use_chroma=False)
            
            # Save metadata for the summary vector index
            import json
            import time
            from pathlib import Path
            
            metadata = {
                "document_name": document_name,
                "index_type": "summary_vector",
                "storage_type": "file",
                "node_count": len(nodes),
                "created_at": str(time.time())
            }
            
            metadata_file = Path(storage_manager.base_dir) / "metadata" / f"{document_name}_summary_vector_metadata.json"
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

    def summary_query(query: str) -> str:
        """Generate a comprehensive summary of the regulatory document.
        
        Args:
            query: The summary request (e.g., "Provide a comprehensive summary")
        """
        try:
            # Use a more targeted approach with smaller chunks
            query_engine = vector_index.as_query_engine(
                similarity_top_k=5,  # Get top 5 most relevant chunks
                response_mode="compact",
                streaming=False,
                response_kwargs={
                    "max_tokens": 1500,  # Limit response length
                    "temperature": 0.1,
                }
            )
            
            # Create a more specific prompt for summary
            summary_prompt = (
                "Based on the most relevant sections of this regulatory order, "
                "provide a comprehensive executive summary that includes: "
                "1) The main purpose and scope of the order, "
                "2) Key decisions and approvals, "
                "3) Important dates and timelines, "
                "4) Major entities involved, "
                "5) Key financial or regulatory implications. "
                "Focus on the most important information and provide a clear, "
                "structured summary suitable for stakeholders."
            )
            
            response = query_engine.query(summary_prompt)
            return str(response)
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    return FunctionTool.from_defaults(
        name="regulatory_summary_tool",
        fn=summary_query,
        description=(
            "Use this tool when you need a comprehensive summary or overview of the entire regulatory order. "
            "This tool provides high-level summaries, executive summaries, or general overviews of the document. "
            "Use this for questions like 'Provide a summary', 'Give me an overview', 'What is this order about', "
            "or when you want to understand the main points and structure of the entire document."
        ),
    )
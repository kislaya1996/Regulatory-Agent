from llama_index.core.tools import FunctionTool, QueryEngineTool
from llama_index.core.schema import BaseNode
from llama_index.core import VectorStoreIndex, DocumentSummaryIndex
from typing import List, Optional
from storage_manager import StorageManager
from custom_llm import llm_retrieval # Assuming this is correctly imported
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.storage import StorageContext
import os
from llama_index.core import Settings

# Ensure LLM and Embedding model are set globally or passed explicitly
# Settings.llm = llm_retrieval # Example: Assuming llm_retrieval is your custom LLM instance
# Settings.embed_model = your_embedding_model_instance # Example: Your custom embed_model

def create_summary_tool(
    nodes: List[BaseNode],
    document_name: str,
    storage_manager: Optional[StorageManager] = None,
    use_chroma: bool = True # This flag is important for ChromaDB integration
) -> FunctionTool:
    """
    Create a summary tool with optional persistence.
    
    Args:
        nodes: List of nodes to create the summary index from
        document_name: Name identifier for the document
        storage_manager: Optional storage manager for persistence
        use_chroma: Whether to use ChromaDB for persistence of the summary index's vectors
    """
    if storage_manager is None:
        raise ValueError("StorageManager must be provided for persistence.")

    print(f"\n--- Setting up Summary Index Tool for {document_name} ---")
    
    # Define paths for ChromaDB collection and LlamaIndex's internal storage for summary index
    chroma_collection_name = f"{document_name}_summary"
    
    # This path is for LlamaIndex's internal components (docstore, index_store)
    # It should be distinct from the ChromaDB data directory.
    summary_index_persist_dir = os.path.join(storage_manager.summary_indexes_dir, document_name)

    # Try to load existing index first
    document_summary_index = None
    if storage_manager:
        try:
            # Pass use_chroma to load_document_summary_index
            document_summary_index = storage_manager.load_document_summary_index(
                document_name, 
                use_chroma=use_chroma
            )
        except Exception as e:
            print(f"Error loading existing summary index: {e}")
            print("Will create new summary index from nodes...")
            document_summary_index = None
    
    # If no existing index, create new one
    if document_summary_index is None:
        print(f"Creating new summary index for {document_name}")
        
        # Initialize ChromaDB client and collection for this specific summary index
        db_summary = chromadb.PersistentClient(path=str(storage_manager.chroma_dir))
        chroma_collection_summary = db_summary.get_or_create_collection(chroma_collection_name)
        
        # Create ChromaVectorStore
        vector_store_summary = ChromaVectorStore(chroma_collection=chroma_collection_summary)
        
        # Create StorageContext using the ChromaVectorStore and the persist_dir for LlamaIndex metadata
        summary_storage_context = StorageContext.from_defaults(
            vector_store=vector_store_summary,
            persist_dir=summary_index_persist_dir # LlamaIndex's internal persistence
        )
        
        # Create DocumentSummaryIndex
        document_summary_index = DocumentSummaryIndex(
            nodes,
            storage_context=summary_storage_context,
            show_progress=True
        )
        
        # Save the index if storage manager is provided
        if storage_manager:
            # Pass use_chroma to save_document_summary_index
            storage_manager.save_document_summary_index(
                document_summary_index, 
                document_name, 
                use_chroma=use_chroma
            )
            print(f"Successfully created and persisted new summary index for {document_name}")
           
    else:
        print(f"Successfully loaded existing document summary index for {document_name}")

    def summary_query(query: str) -> str:
        """Generate a comprehensive summary of the regulatory document.
        
        Args:
            query: The summary request (e.g., "Provide a comprehensive summary")
        """
        try:
            query_engine = document_summary_index.as_query_engine(
                response_mode="compact",
                streaming=False,
                llm=llm_retrieval, # Use the custom LLM
                response_kwargs={
                    "max_tokens": 1500,  # Limit response length
                    "temperature": 0.1,
                }
            )
            
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
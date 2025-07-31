from llama_index.core.tools import FunctionTool, QueryEngineTool
from llama_index.core.schema import BaseNode
from llama_index.core import VectorStoreIndex, DocumentSummaryIndex, SummaryIndex
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
        
        # Create the persist directory first to avoid the FileNotFoundError
        os.makedirs(summary_index_persist_dir, exist_ok=True)
        
        # Initialize ChromaDB client and collection for this specific summary index
        db_summary = chromadb.PersistentClient(path=str(storage_manager.chroma_dir))
        chroma_collection_summary = db_summary.get_or_create_collection(chroma_collection_name)
        
        # Create ChromaVectorStore
        vector_store_summary = ChromaVectorStore(chroma_collection=chroma_collection_summary)
        
        # Create StorageContext without persist_dir first to avoid loading existing components
        summary_storage_context = StorageContext.from_defaults(
            vector_store=vector_store_summary
        )
        
        # Create DocumentSummaryIndex
        document_summary_index = SummaryIndex(
            nodes,
            storage_context=summary_storage_context,
            show_progress=True
        )
        
        # Now persist the index to the specified directory
        document_summary_index.storage_context.persist(persist_dir=summary_index_persist_dir)
        
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
            # Configure query engine with proper settings to avoid input length issues
            query_engine = document_summary_index.as_query_engine(
                response_mode="compact",
                streaming=False,
                llm=llm_retrieval, # Use the custom LLM
                response_kwargs={
                    "max_tokens": 1500,  # Limit response length
                    "temperature": 0.1,
                },
                # Add node filtering to limit input size
                similarity_top_k=5,  # Limit number of nodes retrieved
                node_postprocessors=None,  # Disable postprocessors that might add content
            )
            
            # Create a more focused summary prompt
            summary_prompt = (
                "Based on the most relevant sections of this regulatory order, "
                "provide a concise executive summary that includes: "
                "1) The main purpose and scope of the order, "
                "2) Key decisions and approvals, "
                "3) Important dates and timelines, "
                "4) Major entities involved, "
                "5) Key financial or regulatory implications. "
                "Keep the summary focused and under 1000 words. "
                "If the content is too extensive, focus on the most critical information only."
            )
            
            response = query_engine.query(summary_prompt)
            return str(response)
            
        except Exception as e:
            error_msg = str(e)
            if "Input is too long" in error_msg or "ValidationException" in error_msg:
                # Fallback: try with even more restrictive settings
                try:
                    print("Input too long, trying with more restrictive settings...")
                    fallback_engine = document_summary_index.as_query_engine(
                        response_mode="compact",
                        streaming=False,
                        llm=llm_retrieval,
                        response_kwargs={
                            "max_tokens": 800,
                            "temperature": 0.1,
                        },
                        similarity_top_k=3,  # Even fewer nodes
                    )
                    
                    fallback_prompt = (
                        "Provide a brief summary of the key points from this regulatory order. "
                        "Focus only on the most important decisions and their implications. "
                        "Keep it under 500 words."
                    )
                    
                    fallback_response = fallback_engine.query(fallback_prompt)
                    return str(fallback_response)
                    
                except Exception as fallback_e:
                    return f"Error generating summary (fallback also failed): {str(fallback_e)}"
            else:
                return f"Error generating summary: {error_msg}"

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
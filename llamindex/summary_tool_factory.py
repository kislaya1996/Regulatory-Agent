from llama_index.core.tools import FunctionTool
from llama_index.core.schema import BaseNode
from llama_index.core import SummaryIndex, VectorStoreIndex
from typing import List, Optional, Dict, Any
from storage_manager import StorageManager
from custom_llm import llm_retrieval, llm_indexing, llm_gemini
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.storage import StorageContext
import os
import json
import time
from llama_index.core import Settings

# Ensure LLM and Embedding model are set globally or passed explicitly
Settings.llm = llm_retrieval
# Settings.embed_model = your_embedding_model_instance

def create_summary_tool(
    nodes: List[BaseNode],
    document_name: str,
    storage_manager: Optional[StorageManager] = None,
    use_chroma: bool = True
) -> FunctionTool:
    """
    Create a summary tool with pre-generated summaries for instant retrieval.
    
    Args:
        nodes: List of nodes to create the summary index from
        document_name: Name identifier for the document
        storage_manager: Optional storage manager for persistence
        use_chroma: Whether to use ChromaDB for persistence of the summary index's vectors
    """
    if storage_manager is None:
        raise ValueError("StorageManager must be provided for persistence.")

    print(f"\n--- Setting up Pre-Generated Summary Tool for {document_name} ---")
    
    # Path for storing pre-generated summaries
    summaries_dir = os.path.join(storage_manager.summary_indexes_dir, f"{document_name}_summaries")
    summaries_file = os.path.join(summaries_dir, "node_summaries.json")
    
    print(f"Summaries directory: {summaries_dir}")
    print(f"Summaries file: {summaries_file}")
    
    # Check if summaries already exist
    if os.path.exists(summaries_file):
        print(f"Loading existing pre-generated summaries for {document_name}")
        try:
            with open(summaries_file, 'r') as f:
                node_summaries = json.load(f)
            print(f"Successfully loaded {len(node_summaries)} node summaries")
        except Exception as e:
            print(f"Error loading summaries: {e}")
            node_summaries = {}
    else:
        node_summaries = {}
    
    # If we don't have summaries for all nodes, generate them
    nodes_to_process = []
    for i, node in enumerate(nodes):
        node_id = f"node_{i}"
        if node_id not in node_summaries:
            nodes_to_process.append((i, node))
    
    if nodes_to_process:
        print(f"Need to generate summaries for {len(nodes_to_process)} nodes")
        print(f"Total nodes in document: {len(nodes)}")
        print(f"Existing summaries: {len(node_summaries)}")
        print(f"Missing summaries: {len(nodes_to_process)}")
        print("This will be done once with slow requests to avoid rate limiting...")
        
        # Create summaries directory
        os.makedirs(summaries_dir, exist_ok=True)
        
        # Process nodes one by one with delays to avoid rate limiting
        for idx, (i, node) in enumerate(nodes_to_process):
            try:
                print(f"Processing node {i+1}/{len(nodes_to_process)} (overall progress: {idx+1}/{len(nodes_to_process)})...")
                
                # Get node content
                if hasattr(node, 'text'):
                    content = node.text
                elif hasattr(node, 'content'):
                    content = str(node.content)
                else:
                    content = str(node)
                
                # Create a simple summary using the indexing LLM
                # Use a very focused prompt to get concise summaries
                summary_prompt = f"""Summarize this regulatory document section in 2-3 sentences. Focus on:
1. What this section is about
2. Key decisions, approvals, or requirements mentioned
3. Important dates, entities, or numbers

Content: {content[:2000]}..."""

                print(f"Generating summary for node {i} (content length: {len(content)})")
                
                # Generate summary with retry logic
                summary = None
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = llm_indexing.complete(summary_prompt)
                        summary = str(response)
                        break
                    except Exception as e:
                        print(f"Attempt {attempt + 1} failed: {e}")
                        if attempt < max_retries - 1:
                            print("Waiting 2 seconds before retry...")
                            time.sleep(2)
                        else:
                            print(f"Failed to generate summary for node {i} after {max_retries} attempts")
                            summary = f"Summary generation failed: {str(e)}"
                
                # Store the summary
                node_id = f"node_{i}"
                node_summaries[node_id] = {
                    "summary": summary,
                    "content_length": len(content),
                    "node_type": type(node).__name__,
                    "metadata": getattr(node, 'metadata', {})
                }
                
                print(f"Generated summary for node {i}: {len(summary)} chars")
                print(f"Progress: {idx+1}/{len(nodes_to_process)} nodes completed ({((idx+1)/len(nodes_to_process)*100):.1f}%)")
                
                # Save progress after each node (in case of interruption)
                with open(summaries_file, 'w') as f:
                    json.dump(node_summaries, f, indent=2)
                
                # Add delay between requests to avoid rate limiting
                if idx < len(nodes_to_process) - 1:  # Don't delay after last node
                    print("Waiting 3 seconds before next node...")
                    time.sleep(3)
                    
            except Exception as e:
                print(f"Error processing node {i}: {e}")
                # Store error info
                node_id = f"node_{i}"
                node_summaries[node_id] = {
                    "summary": f"Error generating summary: {str(e)}",
                    "content_length": 0,
                    "node_type": type(node).__name__,
                    "metadata": getattr(node, 'metadata', {})
                }
        
        print(f"Completed generating summaries for all {len(nodes_to_process)} nodes")
        print(f"Total summaries stored: {len(node_summaries)}")
        print(f"Summary generation completed for document: {document_name}")
    
    else:
        print(f"All {len(node_summaries)} node summaries already exist and are ready for instant retrieval")
        print(f"No new summaries needed for document: {document_name}")

    def summary_query(query: str) -> str:
        """Generate a comprehensive summary using pre-generated node summaries.
        
        Args:
            query: The summary request (e.g., "Provide a comprehensive summary")
        """
        
        print(f"\n=== INSTANT SUMMARY QUERY (No LLM calls) ===")
        print(f"Query: {query}")
        print(f"Available node summaries: {len(node_summaries)}")
        
        if not node_summaries:
            return "Error: No pre-generated summaries available. Please regenerate the summary tool."
        
        # Analyze the query to determine what type of summary is needed
        query_lower = query.lower()
        
        # Determine summary strategy based on query
        if "tariff" in query_lower or "fixed charge" in query_lower or "rate" in query_lower:
            # Look for tariff-related information
            relevant_summaries = []
            for node_id, summary_data in node_summaries.items():
                summary_text = summary_data["summary"].lower()
                if any(keyword in summary_text for keyword in ["tariff", "charge", "rate", "price", "cost"]):
                    relevant_summaries.append(summary_data["summary"])
            
            if relevant_summaries:
                return f"Tariff-related information found in {len(relevant_summaries)} sections:\n\n" + "\n\n".join(relevant_summaries[:5])
            else:
                return "No tariff-related information found in this document."
        
        elif "overview" in query_lower or "summary" in query_lower or "about" in query_lower:
            # Provide a general overview using first few summaries
            overview_summaries = list(node_summaries.values())[:5]
            return f"Document Overview:\n\n" + "\n\n".join([s["summary"] for s in overview_summaries])
        
        elif "approval" in query_lower or "decision" in query_lower:
            # Look for approval/decision information
            relevant_summaries = []
            for summary_data in node_summaries.values():
                summary_text = summary_data["summary"].lower()
                if any(keyword in summary_text for keyword in ["approve", "approval", "decision", "grant", "permit"]):
                    relevant_summaries.append(summary_data["summary"])
            
            if relevant_summaries:
                return f"Approval/Decision information found:\n\n" + "\n\n".join(relevant_summaries[:5])
            else:
                return "No specific approval or decision information found."
        
        else:
            # Default: provide a comprehensive summary using all available summaries
            all_summaries = [summary_data["summary"] for summary_data in node_summaries.values()]
            
            # Limit to first 10 summaries to avoid overwhelming response
            if len(all_summaries) > 10:
                return f"Comprehensive Summary (showing first 10 of {len(all_summaries)} sections):\n\n" + "\n\n".join(all_summaries[:10])
            else:
                return f"Comprehensive Summary:\n\n" + "\n\n".join(all_summaries)

    return FunctionTool.from_defaults(
        name="regulatory_summary_tool",
        fn=summary_query,
        description=(
            "Use this tool when you need a comprehensive summary or overview of the entire regulatory order. "
            "This tool provides instant summaries using pre-generated content - no LLM calls needed during queries. "
            "Use this for questions like 'Provide a summary', 'Give me an overview', 'What is this order about', "
            "or when you want to understand the main points and structure of the entire document."
        ),
    )
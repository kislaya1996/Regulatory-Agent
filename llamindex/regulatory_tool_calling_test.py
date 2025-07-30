import os
import requests
import nest_asyncio
import json

# Apply nest_asyncio for environments like Google Colab or Jupyter notebooks
nest_asyncio.apply()

# --- Load environment variables ---
from dotenv import load_dotenv
load_dotenv()

# --- LlamaIndex Imports ---
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import TitleExtractor, QuestionsAnsweredExtractor, SummaryExtractor   
from llama_index.core.ingestion import IngestionPipeline, IngestionCache

from llama_index.core import Settings
from typing import List
from custom_llm import llm_indexing, llm_retrieval
from embedding_model import embed_model
from vector_tool_factory import create_vector_query_tool
from summary_tool_factory import create_summary_tool
from storage_manager import StorageManager

#Update Global LLM and Embedding Model to our custom classes
Settings.llm = llm_indexing
Settings.embed_model = embed_model

# --- Initialize Storage Manager ---
storage_manager = StorageManager(base_dir="./regulatory_storage")

# --- Load Regulatory Document ---
print("\n--- Loading Regulatory Document ---")
filename = "../merc_test_files/orders/MSEDCL-MYT-Order_Case_no_217-of-2024.pdf"

# Check if file exists
if not os.path.exists(filename):
    print(f"Error: File {filename} not found!")
    exit()

print(f"Loading document: {filename}")

# Extract document name from filename for storage
document_name = os.path.splitext(os.path.basename(filename))[0]
print(f"Document name for storage: {document_name}")

# Check if we have existing processed nodes
existing_nodes = storage_manager.load_nodes(document_name)

if existing_nodes:
    print(f"Found existing processed nodes for {document_name}")
    nodes = existing_nodes
else:
    print(f"No existing nodes found, processing document...")
    
    # Alternative approach: Use caching to avoid reprocessing
    # This will cache the results of LLM transformations to avoid making the same API calls again
    pipeline_with_cache = IngestionPipeline(
        transformations=[
            SentenceSplitter(chunk_size=512, chunk_overlap=25),
            # TitleExtractor(nodes=2),  #too slow
        ],
        cache=IngestionCache(
            cache_dir="./cache",
            collection_name="regulatory_docs"
        )
    )

    # Load data and create chunks
    print("Loading data and creating chunks...")
    documents = SimpleDirectoryReader(input_files=[filename]).load_data()
    nodes = pipeline_with_cache.run(documents=documents)
    
    # Save the processed nodes
    storage_manager.save_nodes(nodes, document_name)

print(f"Data loaded and chunked. Total nodes: {len(nodes)}")

# Look at the content of the first chunk
if nodes:
    print("\nContent of the first chunk (with metadata):")
    print(nodes[0].get_content(metadata_mode="all"))

Settings.llm = llm_retrieval

# Create tools with persistence
vector_query_tool = create_vector_query_tool(
    nodes=nodes,
    document_name=document_name,
    storage_manager=storage_manager,
    use_chroma=True
)

summary_tool = create_summary_tool(
    nodes=nodes,
    document_name=document_name,
    storage_manager=storage_manager
)

print("\n--- Testing combined tools (Vector and Summary) with Bedrock Claude Sonnet ---")

print("\nQuery 1: Asking about specific content (should use regulatory_search_tool)")
response_combined_1 = llm_retrieval.predict_and_call(
    [vector_query_tool, summary_tool],
    "What are the tariff rates mentioned in this order?",
    verbose=True
)
print(f"Combined Tool Response 1: {str(response_combined_1)}")
print("Source nodes for Combined Tool Query 1:")
for n in response_combined_1.source_nodes:
    print(n.metadata)

# Display storage information
print("\n--- Storage Information ---")
metadata = storage_manager.get_document_metadata(document_name)
print(f"Document: {document_name}")
print(f"Metadata: {json.dumps(metadata, indent=2)}")

# List all stored documents
print("\n--- All Stored Documents ---")
all_documents = storage_manager.list_documents()
print(f"Stored documents: {all_documents}")

print("\nQuery 2: Asking for a summary (should use regulatory_summary_tool)")
response_combined_2 = llm_retrieval.predict_and_call(
    [vector_query_tool, summary_tool],
    "Provide a comprehensive summary of this regulatory order",
    verbose=True
)
print(f"Combined Tool Response 2: {str(response_combined_2)}")

# print("\nQuery 3: Asking about specific page content")
# response_combined_3 = llm.predict_and_call(
#     [vector_query_tool, summary_tool],
#     "What are the main points discussed on page 2 of this order?",
#     verbose=True
# )
# print(f"Combined Tool Response 3: {str(response_combined_3)}")
# print("Source nodes for Combined Tool Query 3:")
# for n in response_combined_3.source_nodes:
#     print(n.metadata) 
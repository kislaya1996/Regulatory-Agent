import os
import requests
import nest_asyncio
import json # Import json for parsing tool arguments if needed (though BedrockConverse handles much of it)

# Apply nest_asyncio for environments like Google Colab or Jupyter notebooks
nest_asyncio.apply()

# --- Install necessary libraries if running in a new environment (e.g., Colab) ---
# Uncomment and run these if you're not managing dependencies with requirements.txt
# !pip install llama-index==0.10.27
# !pip install llama-index-llms-bedrock-converse
# !pip install llama-index-embeddings-openai
# !pip install boto3
# !pip install python-dotenv
# !pip install requests


# --- Load environment variables ---
from dotenv import load_dotenv
load_dotenv()

# --- Set up AWS credentials from environment variables ---
# LlamaIndex's BedrockConverse can pick these up directly if set as environment variables,
# or you can pass them explicitly.
# os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
# os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
# If you have an AWS profile configured, you can use `profile_name="your_profile"` instead.


# --- LlamaIndex Imports ---
from llama_index.core.tools import FunctionTool, QueryEngineTool
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, SummaryIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.vector_stores import MetadataFilters, FilterCondition
from llama_index.llms.bedrock_converse import BedrockConverse # The recommended LLM
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings
from typing import List


# --- Initialize the LLM (Using LlamaIndex's BedrockConverse) ---
# IMPORTANT: Use the actual model ID for tool calling, not just the inference profile ARN.
# The inference profile ARN you provided:
# "arn:aws:bedrock:ap-south-1:554902127471:inference-profile/apac.anthropic.claude-3-5-sonnet-20241022-v2:0"
# should map to a specific model. For tool calling, it's safer to use the direct model ID
# that the profile is using, typically: "anthropic.claude-3-5-sonnet-20240620-v1:0"
# Please confirm the exact model ID from your Bedrock console or documentation.

embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5",
    cache_folder="./embeddings_cache" # Optional: specify a cache directory
)

# Set the global embedding model for LlamaIndex
Settings.embed_model = embed_model

llm = BedrockConverse(
    model="arn:aws:bedrock:ap-south-1:554902127471:inference-profile/apac.anthropic.claude-3-5-sonnet-20241022-v2:0", # Direct model ID for Claude 3.5 Sonnet
    region_name="ap-south-1",
    # You can also explicitly pass credentials if environment variables aren't preferred:
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    temperature=0,
)

Settings.llm = llm

print("LLM initialized with BedrockConverse using Claude 3.5 Sonnet.")

# --- Creating Function Tools ---
def add(x: int, y: int) -> int:
    """Adds two integers together."""
    return x + y

def mystery(x: int, y: int) -> int:
    """Mystery function that operates on top of two numbers."""
    return (x + y) * (x + y)

add_tool = FunctionTool.from_defaults(fn=add)
mystery_tool = FunctionTool.from_defaults(fn=mystery)

print("\n--- Testing Function Calling with Bedrock Claude Sonnet ---")
response = llm.predict_and_call(
    [add_tool, mystery_tool],
    "Tell me the output of the mystery function on 2 and 9",
    verbose=True
)
print(f"Function Call Response: {str(response)}")

# --- Vector Search with Metadata Setup ---

# Download the PDF
print("\n--- Downloading PDF ---")
url = "https://arxiv.org/pdf/2308.00352"
filename = "MetaGPT.pdf"
try:
    response_pdf = requests.get(url)
    response_pdf.raise_for_status() # Raise an exception for HTTP errors
    with open(filename, "wb") as output_file:
        output_file.write(response_pdf.content)
    print("Successfully downloaded the PDF file")
except requests.exceptions.RequestException as e:
    print(f"Error downloading PDF: {e}")
    # Exit or handle gracefully if PDF download fails, as subsequent steps depend on it.
    exit()

# Load data and create chunks
print("Loading data and creating chunks...")
documents = SimpleDirectoryReader(input_files=[filename]).load_data()
splitter = SentenceSplitter(chunk_size=1024)
nodes = splitter.get_nodes_from_documents(documents)
print("Data loaded and chunked.")

# Look at the content of the first chunk
if nodes:
    print("\nContent of the first chunk (with metadata):")
    print(nodes[0].get_content(metadata_mode="all"))

# Creation of Vector Index
print("\nCreating Vector Index...")
vector_index = VectorStoreIndex(nodes)
print("Vector Index created.")

# Test direct query with metadata filter
print("\n--- Testing direct Vector Query with Metadata Filter ---")
query_engine_filtered = vector_index.as_query_engine(
    similarity_top_k=2,
    filters=MetadataFilters.from_dicts(
        [
            {"key": "page_label", "value": "2"}
        ]
    )
)
response_filtered = query_engine_filtered.query(
    "What are some high-level results of MetaGPT?",
)
print(f"Direct Filtered Query Response (first 100 chars): {str(response_filtered)[:100]}...")
print("Source nodes for direct filtered query:")
for n in response_filtered.source_nodes:
    print(n.metadata)


# --- Retrieval Tool Definition ---
def vector_query(
    query: str,
    page_numbers: List[str]
) -> str:
    """Perform a vector search over an index.

    query (str): the string query to be embedded.
    page_numbers (List[str]): Filter by set of pages. Leave BLANK if we want to perform a vector search
        over all pages. Otherwise, filter by the set of specified pages.

    """
    metadata_dicts = [
        {"key": "page_label", "value": p} for p in page_numbers
    ]

    query_engine = vector_index.as_query_engine(
        similarity_top_k=2,
        filters=MetadataFilters.from_dicts(
            metadata_dicts,
            condition=FilterCondition.OR
        )
    )
    response = query_engine.query(query)
    return str(response)

vector_query_tool = FunctionTool.from_defaults(
    name="vector_tool",
    fn=vector_query,
    description="Tool for performing vector search on the MetaGPT paper, optionally filtering by page numbers."
)

print("\n--- Testing Vector Query Tool with Bedrock Claude Sonnet ---")
response_tool_call = llm.predict_and_call(
    [vector_query_tool],
    "What are the high-level results of MetaGPT as described on page 2?",
    verbose=True
)
print(f"Tool Call Response: {str(response_tool_call)}")
print("Source nodes for tool-called query:")
for n in response_tool_call.source_nodes:
    print(n.metadata)


# --- Add Summary Index Tool ---
print("\n--- Setting up Summary Index Tool ---")
summary_index = SummaryIndex(nodes)
summary_query_engine = summary_index.as_query_engine(
    response_mode="tree_summarize",
    use_async=True,
)
summary_tool = QueryEngineTool.from_defaults(
    name="summary_tool",
    query_engine=summary_query_engine,
    description=(
        "Useful if you want to get a high-level summary of the entire MetaGPT paper."
    ),
)

print("\n--- Testing combined tools (Vector and Summary) with Bedrock Claude Sonnet ---")

print("\nQuery 1: Asking about a specific page (should use vector_tool)")
response_combined_1 = llm.predict_and_call(
    [vector_query_tool, summary_tool],
    "What are the MetaGPT comparisons with ChatDev described on page 8?",
    verbose=True
)
print(f"Combined Tool Response 1: {str(response_combined_1)}")
print("Source nodes for Combined Tool Query 1:")
for n in response_combined_1.source_nodes:
    print(n.metadata)

print("\nQuery 2: Asking for a summary (should use summary_tool)")
response_combined_2 = llm.predict_and_call(
    [vector_query_tool, summary_tool],
    "What is a summary of the paper?",
    verbose=True
)
print(f"Combined Tool Response 2: {str(response_combined_2)}")
# Summary index typically doesn't have source_nodes in the same way as vector index
# but you can inspect the response directly if verbose is true.
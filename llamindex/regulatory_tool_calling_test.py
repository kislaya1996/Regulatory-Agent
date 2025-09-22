import os
import json
import nest_asyncio
import datetime
import concurrent.futures
import time
import random
from functools import wraps

# Apply nest_asyncio for environments like Google Colab or Jupyter notebooks
nest_asyncio.apply()

# --- Load environment variables ---
from dotenv import load_dotenv
load_dotenv()

# --- LlamaIndex Imports ---
from llama_index.core import Settings
from custom_llm import llm_retrieval, llm_indexing
from embedding_model import embed_model
from storage_manager import StorageManager
from tool_cache import ToolCache

# Update Global LLM and Embedding Model to our custom classes
Settings.llm = llm_retrieval
Settings.embed_model = embed_model

# --- Initialize Storage Manager and Tool Cache ---
storage_manager = StorageManager(base_dir="./regulatory_storage")
tool_cache = ToolCache(storage_manager, cache_dir="./tool_cache")

def rate_limited(max_calls_per_minute=30):
    """Decorator to limit API calls per minute to avoid throttling."""
    def decorator(func):
        last_reset = time.time()
        call_count = 0
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal last_reset, call_count
            
            current_time = time.time()
            
            # Reset counter if a minute has passed
            if current_time - last_reset >= 60:
                last_reset = current_time
                call_count = 0
            
            # If we've hit the limit, wait
            if call_count >= max_calls_per_minute:
                sleep_time = 60 - (current_time - last_reset)
                if sleep_time > 0:
                    print(f"  ⏳ Rate limit reached. Waiting {sleep_time:.1f} seconds...")
                    time.sleep(sleep_time)
                    last_reset = time.time()
                    call_count = 0
            
            # Add some jitter to avoid thundering herd
            jitter = random.uniform(0.1, 0.5)
            time.sleep(jitter)
            
            call_count += 1
            
            # Retry logic for throttling exceptions
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "ThrottlingException" in str(e) or "Too many requests" in str(e):
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) + random.uniform(1, 3)
                            print(f"  ⏳ Throttling detected. Retrying in {wait_time:.1f} seconds... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                    raise e
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

@rate_limited(max_calls_per_minute=20)
def safe_llm_call(prompt, verbose=False):
    """Make a rate-limited LLM call with retry logic for final synthesis (uses llm_retrieval)."""
    try:
        if verbose:
            print(f"  🤖 Making LLM call with prompt: {prompt[:100]}...")
        
        # For final synthesis, use llm_retrieval
        response = llm_retrieval.complete(prompt)
        
        if verbose:
            print(f"  📝 LLM response: {str(response)[:200]}...")
        
        return str(response)
            
    except Exception as e:
        print(f"  ⚠️  LLM call failed: {e}")
        # Return a simple fallback response instead of raising
        return "Unable to synthesize response due to LLM error."

@rate_limited(max_calls_per_minute=20)
def safe_llm_indexing_call(prompt, verbose=False):
    """Make a rate-limited LLM call with retry logic for relevance analysis (uses llm_indexing)."""
    try:
        if verbose:
            print(f"  🤖 Making LLM indexing call with prompt: {prompt[:100]}...")
        
        # For relevance analysis, use llm_indexing
        response = llm_indexing.complete(prompt)
        
        if verbose:
            print(f"  📝 LLM indexing response: {str(response)[:200]}...")
        
        return str(response)
            
    except Exception as e:
        print(f"  ⚠️  LLM indexing call failed: {e}")
        # Return a simple fallback response instead of raising
        return "5.0 - Unable to analyze relevance due to LLM error."

def save_exclude_keywords_config(exclude_keywords):
    """Save exclude keywords configuration to a file."""
    config_file = "exclude_keywords_config.json"
    config = {
        "exclude_keywords": exclude_keywords,
        "last_updated": str(datetime.datetime.now())
    }
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"💾 Configuration saved to {config_file}")
    except Exception as e:
        print(f"⚠️  Could not save configuration: {e}")

def load_exclude_keywords_config():
    """Load exclude keywords configuration from file."""
    config_file = "exclude_keywords_config.json"
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config.get("exclude_keywords", ["Marathi"])
    except Exception as e:
        print(f"⚠️  Could not load configuration: {e}")
    
    return ["Marathi"]  # Default fallback

def get_exclude_keywords():
    """Get keywords to exclude from environment variables, config file, or user input."""
    # Try to get from environment variable first
    exclude_env = os.getenv('EXCLUDE_KEYWORDS')
    if exclude_env:
        exclude_keywords = [kw.strip() for kw in exclude_env.split(',') if kw.strip()]
        print(f"📋 Using exclude keywords from environment: {exclude_keywords}")
        return exclude_keywords
    
    # Try to load from config file
    exclude_keywords = load_exclude_keywords_config()
    
    print(f"\n--- Document Filtering Configuration ---")
    print(f"Current exclude keywords: {exclude_keywords}")
    print("Options:")
    print("  'keep' - Use current settings")
    print("  'add:keyword' - Add a keyword to exclude")
    print("  'remove:keyword' - Remove a keyword from exclude list")
    print("  'clear' - Clear all exclude keywords")
    print("  'custom:keyword1,keyword2' - Set custom exclude keywords")
    print("  'save' - Save current configuration")
    
    while True:
        choice = input("\nEnter your choice (or press Enter to keep current): ").strip()
        
        if not choice or choice.lower() == 'keep':
            return exclude_keywords
        
        elif choice.lower() == 'clear':
            exclude_keywords = []
            save_exclude_keywords_config(exclude_keywords)
            return exclude_keywords
        
        elif choice.lower() == 'save':
            save_exclude_keywords_config(exclude_keywords)
            return exclude_keywords
        
        elif choice.lower().startswith('add:'):
            keyword = choice[4:].strip()
            if keyword:
                exclude_keywords.append(keyword)
                print(f"Added '{keyword}' to exclude list: {exclude_keywords}")
                save_exclude_keywords_config(exclude_keywords)
                return exclude_keywords
            else:
                print("Please provide a keyword to add")
                continue
        
        elif choice.lower().startswith('remove:'):
            keyword = choice[7:].strip()
            if keyword in exclude_keywords:
                exclude_keywords.remove(keyword)
                print(f"Removed '{keyword}' from exclude list: {exclude_keywords}")
                save_exclude_keywords_config(exclude_keywords)
                return exclude_keywords
            else:
                print(f"Keyword '{keyword}' not found in exclude list")
                continue
        
        elif choice.lower().startswith('custom:'):
            keywords_str = choice[7:].strip()
            if keywords_str:
                exclude_keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
                print(f"Set custom exclude keywords: {exclude_keywords}")
                save_exclude_keywords_config(exclude_keywords)
                return exclude_keywords
            else:
                print("Please provide keywords separated by commas")
                continue
        
        else:
            print("Invalid choice. Please try again.")
            continue

def preview_document_filtering(exclude_keywords):
    """Preview which documents will be excluded based on keywords."""
    if not exclude_keywords:
        return
    
    all_documents = storage_manager.list_documents()
    excluded_documents = []
    
    for doc in all_documents:
        doc_lower = doc.lower()
        if any(keyword.lower() in doc_lower for keyword in exclude_keywords):
            excluded_documents.append(doc)
    
    if excluded_documents:
        print(f"\n🔍 Document Filtering Preview:")
        print(f"   Exclude keywords: {', '.join(exclude_keywords)}")
        print(f"   Documents that will be excluded: {len(excluded_documents)}")
        print(f"   Documents that will be included: {len(all_documents) - len(excluded_documents)}")
        
        print(f"\n   Excluded documents:")
        for doc in excluded_documents[:10]:  # Show first 10
            print(f"     ❌ {doc}")
        if len(excluded_documents) > 10:
            print(f"     ... and {len(excluded_documents) - 10} more")
        
        print(f"\n   Sample included documents:")
        included_docs = [doc for doc in all_documents if doc not in excluded_documents]
        for doc in included_docs[:5]:  # Show first 5
            print(f"     ✅ {doc}")
        if len(included_docs) > 5:
            print(f"     ... and {len(included_docs) - 5} more")

def load_all_document_tools(force_rebuild: bool = False, exclude_keywords: list = None):
    """Load tools for all available indexed documents using cache."""
    all_documents = storage_manager.list_documents()
    
    if not all_documents:
        print("No indexed documents found!")
        return {}
    
    # Filter out documents with excluded keywords
    if exclude_keywords:
        original_count = len(all_documents)
        filtered_documents = []
        excluded_documents = []
        
        for doc in all_documents:
            doc_lower = doc.lower()
            if any(keyword.lower() in doc_lower for keyword in exclude_keywords):
                excluded_documents.append(doc)
            else:
                filtered_documents.append(doc)
        
        all_documents = filtered_documents
        
        print(f"\n--- Document Filtering ---")
        print(f"Original documents: {original_count}")
        print(f"Excluded documents: {len(excluded_documents)}")
        print(f"Filtered documents: {len(all_documents)}")
        
        if excluded_documents:
            print(f"Excluded keywords: {', '.join(exclude_keywords)}")
            print(f"Excluded documents:")
            for doc in excluded_documents[:5]:  # Show first 5
                print(f"  - {doc}")
            if len(excluded_documents) > 5:
                print(f"  ... and {len(excluded_documents) - 5} more")
            
            # Clear cache for excluded documents to prevent them from being loaded
            print(f"\n🧹 Clearing cache for excluded documents...")
            for doc in excluded_documents:
                tool_cache.clear_cache(doc)
            print(f"✅ Cleared cache for {len(excluded_documents)} excluded documents")
            
            # Also clear memory cache to ensure no excluded documents remain
            print(f"🧹 Clearing memory cache to ensure clean state...")
            tool_cache._tools_cache.clear()
            print(f"✅ Memory cache cleared")
    
    print(f"\n--- Loading Tools for {len(all_documents)} Documents ---")
    print("Using tool cache for faster loading...")
    
    # Verify filtered document list doesn't contain excluded documents
    if exclude_keywords:
        excluded_in_filtered = []
        for doc in all_documents:
            doc_lower = doc.lower()
            if any(keyword.lower() in doc_lower for keyword in exclude_keywords):
                excluded_in_filtered.append(doc)
        
        if excluded_in_filtered:
            print(f"\n❌ ERROR: Found {len(excluded_in_filtered)} excluded documents in filtered list:")
            for doc in excluded_in_filtered:
                print(f"   - {doc}")
            print(f"   This should not happen - filtering logic has failed")
        else:
            print(f"\n✅ Filtered document list verification passed")
    
    # Track processing statistics
    total_docs = len(all_documents)
    processed_docs = 0
    cached_docs = 0
    error_docs = 0
    
    # Use the cache to load all tools
    document_tools = tool_cache.get_tools_for_documents(all_documents, force_rebuild=force_rebuild)
    
    # Debug: Show exactly which documents were loaded
    if exclude_keywords:
        print(f"\n🔍 DEBUG: Documents loaded into document_tools:")
        for doc_name in document_tools.keys():
            doc_lower = doc_name.lower()
            excluded = any(keyword.lower() in doc_lower for keyword in exclude_keywords)
            status = "❌ EXCLUDED" if excluded else "✅ INCLUDED"
            print(f"   {status}: {doc_name}")
    
    # Count statistics from results
    for doc_name, doc_info in document_tools.items():
        processed_docs += 1
        if doc_info.get('metadata', {}).get('cached', False):
            cached_docs += 1
    
    error_docs = total_docs - processed_docs
    
    print(f"\n📊 Document Processing Summary:")
    print(f"   Total documents: {total_docs}")
    print(f"   Successfully processed: {processed_docs}")
    print(f"   From cache: {cached_docs}")
    print(f"   Newly built: {processed_docs - cached_docs}")
    print(f"   Failed to load: {error_docs}")
    
    # Show cache statistics
    cache_stats = tool_cache.get_cache_stats()
    print(f"\n📊 Cache Statistics:")
    print(f"   Total cached documents: {cache_stats['total_cached_documents']}")
    print(f"   Memory cache size: {cache_stats['memory_cache_size']}")
    print(f"   Cache directory: {cache_stats['cache_dir']}")
    
    # Verify that excluded documents are not in the final result
    if exclude_keywords:
        excluded_in_result = []
        for doc_name in document_tools.keys():
            doc_lower = doc_name.lower()
            if any(keyword.lower() in doc_lower for keyword in exclude_keywords):
                excluded_in_result.append(doc_name)
        
        if excluded_in_result:
            print(f"\n⚠️  WARNING: Found {len(excluded_in_result)} excluded documents still in results:")
            for doc in excluded_in_result:
                print(f"   ❌ {doc}")
            print(f"   Removing excluded documents from final results...")
            
            # Remove excluded documents from the final result
            for doc_name in excluded_in_result:
                document_tools.pop(doc_name, None)
                print(f"   🗑️  Removed: {doc_name}")
            
            print(f"   ✅ Final document count after cleanup: {len(document_tools)}")
        else:
            print(f"\n✅ Verification passed: No excluded documents found in final results")
    
    return document_tools

def display_document_menu(document_tools):
    """Display a menu of available documents."""
    print(f"\n--- Available Documents ({len(document_tools)}) ---")
    
    for i, (doc_name, doc_info) in enumerate(document_tools.items(), 1):
        node_count = doc_info['node_count']
        has_vector = bool(doc_info['metadata'].get('vector_index'))
        has_summary = bool(doc_info['metadata'].get('summary_index'))
        
        status = []
        if has_vector:
            status.append("🔍 Vector")
        if has_summary:
            status.append("📝 Summary")
        
        status_str = ", ".join(status) if status else "❌ No indexes"
        
        print(f"{i:3d}. {doc_name}")
        print(f"     Nodes: {node_count}, Indexes: {status_str}")

def select_relevant_documents_by_query(selected_docs, user_query, max_docs=10):
    """Intelligently select documents based on user query using LLM analysis."""
    print(f"\n🧠 Smart Document Selection Based on Query")
    print(f"Analyzing query to identify most relevant documents...")
    
    # Create a prompt for the LLM to analyze document names
    document_names = list(selected_docs)
    
    analysis_prompt = f"""
    Based on the user's query, analyze the following document names and identify which documents are most likely to contain relevant information.

    USER QUERY: {user_query}

    AVAILABLE DOCUMENTS:
    {chr(10).join([f"{i+1}. {doc}" for i, doc in enumerate(document_names)])}

    TASK: 
    1. Identify documents that are most likely to contain information relevant to the query
    2. Consider document names, keywords, and context
    3. Return a list of document names (not numbers) that should be analyzed
    4. Focus on documents that match the query intent (e.g., "tariff orders" for tariff queries)
    5. Limit to maximum {max_docs} documents for performance

    RESPONSE FORMAT:
    Return only the document names, one per line, like this:
    Document-Name-1
    Document-Name-2
    Document-Name-3

    ANALYSIS:
    """
    
    try:
        # Use rate-limited LLM to analyze and select relevant documents
        print(f"  🤖 Using LLM to analyze {len(document_names)} documents...")
        
        response = safe_llm_indexing_call(analysis_prompt, verbose=False)
        
        # Parse the response to extract document names
        selected_doc_names = []
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                # Remove any numbering or formatting
                if '. ' in line:
                    line = line.split('. ', 1)[1]
                
                # Check if this document name exists in our list
                if line in document_names:
                    selected_doc_names.append(line)
                else:
                    # Try partial matching
                    for doc_name in document_names:
                        if line.lower() in doc_name.lower() or doc_name.lower() in line.lower():
                            if doc_name not in selected_doc_names:
                                selected_doc_names.append(doc_name)
                                break
        
        # If LLM didn't select enough documents, add some based on keyword matching
        if len(selected_doc_names) < max_docs:
            print(f"  🔍 LLM selected {len(selected_doc_names)} documents, adding keyword-based matches...")
            
            # Extract key terms from the query
            query_lower = user_query.lower()
            priority_keywords = []
            
            if 'tariff' in query_lower:
                priority_keywords.extend(['tariff', 'order', 'regulation'])
            if 'fixed charge' in query_lower or 'charge' in query_lower:
                priority_keywords.extend(['charge', 'tariff', 'order'])
            if 'discom' in query_lower or 'msedcl' in query_lower or 'aeml' in query_lower or 'tata' in query_lower:
                priority_keywords.extend(['discom', 'msedcl', 'aeml', 'tata'])
            if 'renewable' in query_lower or 'solar' in query_lower or 'wind' in query_lower:
                priority_keywords.extend(['re', 'renewable', 'solar', 'wind'])
            
            # Add documents that match keywords but weren't selected by LLM
            for doc_name in document_names:
                if len(selected_doc_names) >= max_docs:
                    break
                    
                doc_lower = doc_name.lower()
                if doc_name not in selected_doc_names:
                    if any(keyword in doc_lower for keyword in priority_keywords):
                        selected_doc_names.append(doc_name)
        
        # Ensure we don't exceed max_docs
        selected_doc_names = selected_doc_names[:max_docs]
        
        print(f"  ✅ Selected {len(selected_doc_names)} documents for analysis:")
        for doc in selected_doc_names:
            print(f"    📄 {doc}")
        
        return selected_doc_names
        
    except Exception as e:
        print(f"  ⚠️  LLM analysis failed: {e}")
        print(f"  🔄 Falling back to keyword-based selection...")
        
        # Fallback: use keyword-based selection
        query_lower = user_query.lower()
        priority_keywords = ['tariff', 'order', 'regulation', 'charge', 'discom', 'msedcl', 'aeml', 'tata', 're', 'renewable']
        
        priority_docs = []
        other_docs = []
        
        for doc in document_names:
            doc_lower = doc.lower()
            if any(keyword in doc_lower for keyword in priority_keywords):
                priority_docs.append(doc)
            else:
                other_docs.append(doc)
        
        # Take priority docs first, then fill with others
        selected_doc_names = priority_docs[:max_docs]
        if len(selected_doc_names) < max_docs:
            selected_doc_names.extend(other_docs[:max_docs - len(selected_doc_names)])
        
        print(f"  ✅ Selected {len(selected_doc_names)} documents using keyword matching:")
        for doc in selected_doc_names:
            print(f"    📄 {doc}")
        
        return selected_doc_names

def test_llm_functionality():
    """Test if the LLM indexing is working properly."""
    try:
        test_prompt = "Answer with just a number between 1 and 10: What is 5 + 3?"
        print(f"🧪 Testing LLM indexing functionality...")
        response = safe_llm_indexing_call(test_prompt, verbose=True)
        print(f"✅ LLM indexing test response: {response}")
        return True
    except Exception as e:
        print(f"❌ LLM indexing test failed: {e}")
        return False

def create_synthesis_query(test_query, all_responses, max_summary_length=500):
    """Create a synthesis query with comprehensive information from all relevant documents."""
    
    # For comprehensive analysis, we want to include more information
    # Let's be more strategic about what we include
    processed_responses = []
    total_length = 0
    max_total_length = 8000  # Increased limit for more comprehensive synthesis
    
    # Sort responses by relevance score to prioritize the most relevant documents
    sorted_responses = sorted(all_responses, key=lambda x: x['relevance_score'], reverse=True)
    
    for resp in sorted_responses:
        # For highly relevant documents (score >= 7), include more content
        if resp['relevance_score'] >= 7.0:
            content_length = min(max_summary_length * 2, 1000)  # More content for highly relevant docs
        elif resp['relevance_score'] >= 5.0:
            content_length = max_summary_length  # Standard content for moderately relevant docs
        else:
            content_length = max_summary_length // 2  # Less content for less relevant docs
        
        truncated_content = truncate_summary_for_synthesis(resp['response'], content_length)
        
        # Estimate the length this response will add to the query
        response_entry = f"Document: {resp['document']} (Relevance: {resp['relevance_score']:.1f})\nContent: {truncated_content}\n\n"
        estimated_length = len(response_entry)
        
        # Check if adding this response would exceed the limit
        if total_length + estimated_length > max_total_length:
            print(f"  ⚠️  Stopping at {len(processed_responses)} responses to avoid input length limit")
            break
        
        processed_responses.append({
            'document': resp['document'],
            'relevance_score': resp['relevance_score'],
            'content': truncated_content
        })
        total_length += estimated_length
    
    # Create a more comprehensive synthesis query
    synthesis_query = f"""
    Based on the following comprehensive information from multiple regulatory documents, provide a detailed and complete answer to this question:

    QUESTION: {test_query['query']}

    DOCUMENT INFORMATION (ranked by relevance):
    {chr(10).join([f"Document: {resp['document']} (Relevance: {resp['relevance_score']:.1f})\nContent: {resp['content']}" for resp in processed_responses])}

    Please provide a comprehensive and detailed answer that:
    1. Addresses the specific question completely with all available information
    2. Includes exact numbers, years, tariff rates, fixed charges, and discom names (MSEDCL, AEML, TATA, etc.)
    3. Synthesizes information from multiple sources comprehensively
    4. Organizes the response logically with clear sections
    5. Highlights any patterns, trends, or changes in the data over time
    6. Prioritizes information from the most relevant documents (higher relevance scores)
    7. Includes all specific details, rates, and regulatory decisions found in the documents
    8. Provides complete context and background information where available
    9. Mentions any limitations or gaps in the available information
    10. Uses the most comprehensive information available from the highest-scoring documents

    IMPORTANT: Be thorough and include ALL relevant information found in the documents. Do not summarize or omit important details.
    """
    
    return synthesis_query, len(processed_responses)

def query_documents(selected_docs, document_tools):
    """Query the selected documents using a two-phase approach with performance optimizations."""
    print(f"\n--- Querying {len(selected_docs)} Documents ---")

    test_query = get_user_query()
    
    print(f"\n{'='*60}")
    print(f"Query: {test_query['name']}")
    print(f"Description: {test_query['description']}")
    
    # Performance optimization: Limit the number of documents to analyze
    processing_mode = test_query.get('mode', 'fast')  # Default to fast mode
    
    if processing_mode == 'fast':
        max_docs_to_analyze = 20  # Only analyze top 20 documents for speed
        max_docs_to_query = 8  # Query only top 8 for speed
    else:  # comprehensive mode
        max_docs_to_analyze = 40  # Analyze top 40 documents
        max_docs_to_query = 15  # Query top 15 documents for comprehensive analysis
    
    # Enforce exclude keywords at query time as a hard guard
    exclude_env = os.getenv('EXCLUDE_KEYWORDS')
    if exclude_env:
        active_exclude_keywords = [kw.strip().lower() for kw in exclude_env.split(',') if kw.strip()]
    else:
        active_exclude_keywords = [kw.lower() for kw in load_exclude_keywords_config() or []]
    
    def _is_excluded(doc_name: str) -> bool:
        return any(kw in doc_name.lower() for kw in active_exclude_keywords)
    
    if active_exclude_keywords:
        filtered_selected_docs = [d for d in selected_docs if not _is_excluded(d)]
        if len(filtered_selected_docs) != len(selected_docs):
            print(f"\n🚫 Enforcing ignore keywords at query-time: {', '.join(active_exclude_keywords)}")
            print(f"   Removed {len(selected_docs) - len(filtered_selected_docs)} documents before selection")
        else:
            print(f"\n✅ No documents matched ignore keywords before selection")
    else:
        filtered_selected_docs = list(selected_docs)
    
    # Smart document selection based on query
    docs_to_analyze = select_relevant_documents_by_query(filtered_selected_docs, test_query['query'], max_docs_to_analyze)
    
    # Re-filter after LLM selection to guarantee enforcement
    if active_exclude_keywords:
        before_count = len(docs_to_analyze)
        docs_to_analyze = [d for d in docs_to_analyze if not _is_excluded(d)]
        removed_after_selection = before_count - len(docs_to_analyze)
        if removed_after_selection > 0:
            print(f"   🚫 Removed {removed_after_selection} documents after selection due to ignore keywords")
    
    print(f"🚀 Smart document selection ({processing_mode} mode): Analyzing {len(docs_to_analyze)} most relevant documents")
    
    # Collect tools for documents to analyze
    summary_tools = []
    vector_tools = []
    doc_names_to_analyze = []
    
    for doc_name in docs_to_analyze:
        doc_info = document_tools[doc_name]
        summary_tools.append(doc_info['summary_tool'])
        vector_tools.append(doc_info['vector_tool'])
        doc_names_to_analyze.append(doc_name)
    
    print(f"Loaded {len(summary_tools)} summary tools and {len(vector_tools)} vector tools")
    
    print(f"Documents to analyze: {len(docs_to_analyze)}")
    print(f"{'='*60}")
    
    # Test LLM functionality before starting analysis
    print(f"\n🧪 Testing LLM indexing functionality for relevance analysis...")
    llm_working = test_llm_functionality()
    if not llm_working:
        print(f"⚠️  LLM indexing not working properly, will use fallback keyword-based scoring")
    
    try:
        # Phase 1: Use summary tools to identify relevant documents (with parallel processing)
        print(f"\n🔍 Phase 1: Document Relevance Analysis (Optimized)")
        print(f"Using {len(summary_tools)} summary tools to identify relevant documents...")
        
        start_time = time.time()
        
        # Use parallel processing for faster analysis
        print(f"  🚀 Using parallel processing for faster analysis...")
        
        # Reduce workers to avoid throttling
        max_workers = min(2, len(docs_to_analyze))  # Use max 2 workers to avoid rate limits
        print(f"  📊 Using {max_workers} parallel workers to avoid API throttling...")
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all analysis tasks
                future_to_doc = {
                    executor.submit(analyze_document_relevance, doc_name, summary_tool, test_query): doc_name
                    for doc_name, summary_tool in zip(doc_names_to_analyze, summary_tools)
                }
                
                # Collect results as they complete
                analysis_results = []
                completed = 0
                failed = 0
                
                for future in concurrent.futures.as_completed(future_to_doc):
                    try:
                        result = future.result()
                        analysis_results.append(result)
                        completed += 1
                        
                        # Show progress
                        if completed % 2 == 0 or completed == len(docs_to_analyze):
                            print(f"    Progress: {completed}/{len(docs_to_analyze)} documents analyzed")
                            
                    except Exception as e:
                        failed += 1
                        doc_name = future_to_doc[future]
                        print(f"    ❌ Failed to analyze {doc_name}: {e}")
                        
                        # Add a failed result
                        analysis_results.append({
                            'doc_name': doc_name,
                            'relevance_score': 0.0,
                            'summary_response': f"Error: {str(e)}"
                        })
                        completed += 1
                        
                        # If too many failures, switch to sequential processing
                        if failed >= 3:
                            print(f"    ⚠️  Too many parallel processing failures, switching to sequential...")
                            break
                            
        except Exception as e:
            print(f"    ⚠️  Parallel processing failed: {e}")
            print(f"    🔄 Falling back to sequential processing...")
            
            # Sequential fallback
            analysis_results = []
            for doc_name, summary_tool in zip(doc_names_to_analyze, summary_tools):
                try:
                    result = analyze_document_relevance(doc_name, summary_tool, test_query)
                    analysis_results.append(result)
                    print(f"    Progress: {len(analysis_results)}/{len(docs_to_analyze)} documents analyzed")
                except Exception as e2:
                    print(f"    ❌ Failed to analyze {doc_name}: {e2}")
                    analysis_results.append({
                        'doc_name': doc_name,
                        'relevance_score': 0.0,
                        'summary_response': f"Error: {str(e2)}"
                    })

        analysis_time = time.time() - start_time
        print(f"  ✅ Analysis completed in {analysis_time:.1f} seconds")
        
        # Process results
        relevant_docs = []
        doc_relevance_scores = {}
        
        for result in analysis_results:
            doc_name = result['doc_name']
            relevance_score = result['relevance_score']
            summary_response = result['summary_response']
            
            doc_relevance_scores[doc_name] = relevance_score
            
            if relevance_score >= 4.0:  # Threshold for relevance (0-10 scale)
                relevant_docs.append(doc_name)
                print(f"    ✅ {doc_name} (score: {relevance_score:.1f})")
            else:
                print(f"    ❌ {doc_name} (score: {relevance_score:.1f})")
        
        # Enforce exclude keywords on relevant docs as a final guard
        if active_exclude_keywords and relevant_docs:
            before_len = len(relevant_docs)
            relevant_docs = [d for d in relevant_docs if not _is_excluded(d)]
            removed_rel = before_len - len(relevant_docs)
            if removed_rel > 0:
                print(f"\n🚫 Removed {removed_rel} relevant documents due to ignore keywords before querying")
        
        # Sort relevant documents by relevance score
        relevant_docs.sort(key=lambda x: doc_relevance_scores.get(x, 0.0), reverse=True)
        
        print(f"\n📊 Document Relevance Results:")
        print(f"  Total documents analyzed: {len(docs_to_analyze)}")
        print(f"  Relevant documents found: {len(relevant_docs)}")
        print(f"  Analysis time: {analysis_time:.1f} seconds")
        
        if relevant_docs:
            print(f"  Relevant documents (ranked by relevance):")
            for doc in relevant_docs[:10]:  # Show top 10
                score = doc_relevance_scores.get(doc, 0.0)
                print(f"    ✅ {doc} (score: {score:.1f})")
            if len(relevant_docs) > 10:
                print(f"    ... and {len(relevant_docs) - 10} more")
            
            # Phase 2: Detailed Information Extraction (Comprehensive)
            print(f"\n🔍 Phase 2: Detailed Information Extraction (Comprehensive)")
            print(f"Using multiple query approaches to retrieve ALL relevant information from each document...")
            # Apply ignore keywords again before limiting to top N
            filtered_relevant_docs = [d for d in relevant_docs if not _is_excluded(d)] if active_exclude_keywords else list(relevant_docs)
            docs_to_query = filtered_relevant_docs[:max_docs_to_query]
            
            print(f"Querying top {len(docs_to_query)} most relevant documents with comprehensive retrieval...")
            
            all_responses = []
            source_documents = set()
            
            start_time = time.time()
            
            for doc_name in docs_to_query:
                if active_exclude_keywords and _is_excluded(doc_name):
                    print(f"  ⏭️  Skipping excluded doc: {doc_name}")
                    continue
                try:
                    print(f"  Querying {doc_name} (relevance: {doc_relevance_scores.get(doc_name, 0.0):.1f})...")
                    
                    # Use the comprehensive retrieval function to get ALL relevant information
                    vector_response = retrieve_comprehensive_document_information(
                        doc_name, document_tools, test_query, storage_manager
                    )
                    
                    if len(vector_response) > 50:  # Only include substantial responses
                        all_responses.append({
                            'document': doc_name,
                            'response': vector_response,
                            'length': len(vector_response),
                            'relevance_score': doc_relevance_scores.get(doc_name, 0.0)
                        })
                        source_documents.add(doc_name)
                        print(f"    ✅ Retrieved {len(vector_response)} characters of information")
                    else:
                        print(f"    ⚠️  Insufficient information ({len(vector_response)} chars)")
                        
                except Exception as e:
                    print(f"    ❌ Error querying {doc_name}: {e}")
                    continue
    
            extraction_time = time.time() - start_time
            print(f"  ✅ Information extraction completed in {extraction_time:.1f} seconds")
            
            # Phase 3: Collate and synthesize responses
            print(f"\n🔍 Phase 3: Response Synthesis")
            print(f"Collating information from {len(all_responses)} document responses...")
            
            if all_responses:
                # Sort responses by relevance score
                all_responses.sort(key=lambda x: x['relevance_score'], reverse=True)
                
                # Create a synthesis query with truncated summaries
                print(f"  📝 Creating synthesis query with truncated summaries...")
                synthesis_query, num_responses_used = create_synthesis_query(test_query, all_responses)
                
                print(f"  📊 Using {num_responses_used}/{len(all_responses)} responses for synthesis")
                print(f"  📏 Synthesis query length: {len(synthesis_query)} characters")
                
                # Use the LLM to synthesize the final response
                print(f"  Synthesizing final response...")
                
                start_time = time.time()
                
                # Use the LLM to synthesize the final response
                try:
                    final_response = safe_llm_call(synthesis_query)
                    
                    synthesis_time = time.time() - start_time
                    
                    print(f"\n🎯 Final Synthesized Response (generated in {synthesis_time:.1f}s):")
                    print(f"{'='*60}")
                    print(f"{final_response}")
                    print(f"{'='*60}")
                    
                except Exception as e:
                    print(f"  ⚠️  Error during synthesis: {e}")
                    
                    # Check if it's an input length error
                    if "Input too long" in str(e) or "too long" in str(e).lower():
                        print(f"  🔄 Input still too long, trying with more restrictive settings...")
                        
                        # Try with even more restrictive settings
                        try:
                            synthesis_query_restrictive, num_responses_used = create_synthesis_query(test_query, all_responses, max_summary_length=100)
                            print(f"  📊 Using {num_responses_used} responses with 100-char summaries")
                            
                            final_response = safe_llm_call(synthesis_query_restrictive)
                            
                            synthesis_time = time.time() - start_time
                            
                            print(f"\n🎯 Final Synthesized Response (restrictive mode, generated in {synthesis_time:.1f}s):")
                            print(f"{'='*60}")
                            print(f"{final_response}")
                            print(f"{'='*60}")
                            
                        except Exception as e2:
                            print(f"  ❌ Still failing: {e2}")
                            print(f"  Falling back to concatenated responses...")
                            
                            # Fallback: concatenate responses
                            final_response = f"Information from {len(all_responses)} relevant documents (ranked by relevance):\n\n"
                            for resp in all_responses[:3]:  # Limit to top 3 for fallback
                                final_response += f"--- {resp['document']} (Relevance: {resp['relevance_score']:.1f}) ---\n{resp['response'][:300]}...\n\n"
                            
                            print(f"\n📋 Concatenated Response (fallback):")
                            print(f"{'='*60}")
                            print(f"{final_response}")
                            print(f"{'='*60}")
                    else:
                        print(f"  Falling back to concatenated responses...")
                        
                        # Fallback: concatenate responses
                        final_response = f"Information from {len(all_responses)} relevant documents (ranked by relevance):\n\n"
                        for resp in all_responses:
                            final_response += f"--- {resp['document']} (Relevance: {resp['relevance_score']:.1f}) ---\n{resp['response'][:300]}...\n\n"
                        
                        print(f"\n📋 Concatenated Response:")
                        print(f"{'='*60}")
                        print(f"{final_response}")
                        print(f"{'='*60}")
            
            # Show source documents with relevance scores
            print(f"\n📚 Source Documents Used (with relevance scores):")
            for resp in all_responses[:num_responses_used]:
                print(f"  - {resp['document']} (score: {resp['relevance_score']:.1f})")
            
            # Show performance summary
            total_time = analysis_time + extraction_time + synthesis_time
            print(f"\n⚡ Performance Summary:")
            print(f"  Analysis time: {analysis_time:.1f}s")
            print(f"  Extraction time: {extraction_time:.1f}s")
            print(f"  Synthesis time: {synthesis_time:.1f}s")
            print(f"  Total time: {total_time:.1f}s")
            print(f"  Documents analyzed: {len(docs_to_analyze)}")
            print(f"  Documents queried: {len(docs_to_query)}")
            print(f"  Responses used for synthesis: {num_responses_used}")
                
        else:
            print(f"  ❌ No relevant documents found for this query")
            print(f"  Consider:")
            print(f"    - Broadening your search terms")
            print(f"    - Checking if documents contain the expected information")
            print(f"    - Using different keywords")
            
            # Show top documents by relevance score for debugging
            print(f"\n🔍 Top documents by relevance score:")
            sorted_docs = sorted(doc_relevance_scores.items(), key=lambda x: x[1], reverse=True)
            for doc_name, score in sorted_docs[:5]:
                print(f"  - {doc_name}: {score:.1f}")
        
    except Exception as e:
        print(f"Error during query: {e}")
        import traceback
        traceback.print_exc()

def calculate_document_relevance(summary_response, test_query):
    """Calculate relevance score for a document using LLM analysis against the actual test query."""
    try:
        # First, test if LLM is working
        if not hasattr(llm_indexing, 'complete'):
            print(f"    ⚠️  LLM indexing not available, using fallback scoring")
            return fallback_relevance_score(summary_response, test_query)
        
        # Create a prompt for the LLM to analyze relevance
        relevance_prompt = f"""
        Analyze the relevance of a document summary to a specific query.

        QUERY: {test_query['query']}

        DOCUMENT SUMMARY: {summary_response}

        TASK: Rate the relevance of this document to the query on a scale of 0-10, where:
        - 0-2: Not relevant at all
        - 3-4: Slightly relevant, may contain some related information
        - 5-6: Moderately relevant, contains useful information
        - 7-8: Highly relevant, directly addresses the query
        - 9-10: Extremely relevant, comprehensive coverage of the query

        Consider:
        1. Does the document contain information that directly answers the query?
        2. Are the key terms and concepts from the query present in the document?
        3. Does the document provide specific data, numbers, or details relevant to the query?
        4. Is the information current and applicable to the query context?

        RESPONSE FORMAT:
        Return only a number between 0-10, followed by a brief explanation (1-2 sentences max).

        Example: "7.5 - Document contains specific tariff rates and discom information relevant to the query."
        """
        
        # Use the LLM to analyze relevance
        print(f"    🔍 Analyzing relevance for document summary: {summary_response[:50]}...")
        response = safe_llm_indexing_call(relevance_prompt, verbose=False)
        print(f"    🤖 LLM response: {response[:100]}...")
        
        # Extract the numerical score from the response
        try:
            # Look for a number at the beginning of the response
            import re
            score_match = re.search(r'^(\d+(?:\.\d+)?)', response.strip())
            if score_match:
                score = float(score_match.group(1))
                # Ensure score is within valid range
                score = max(0.0, min(10.0, score))
                print(f"    ✅ Extracted score: {score}")
                return score
            else:
                # Fallback: try to extract any number from the response
                numbers = re.findall(r'\d+(?:\.\d+)?', response)
                if numbers:
                    score = float(numbers[0])
                    score = max(0.0, min(10.0, score))
                    print(f"    ✅ Extracted score from response: {score}")
                    return score
                else:
                    # If no number found, use fallback scoring
                    print(f"    ⚠️  No number found in LLM response, using fallback scoring")
                    return fallback_relevance_score(summary_response, test_query)
        except (ValueError, IndexError) as e:
            print(f"    ⚠️  Error parsing LLM response: {e}")
            # If parsing fails, use a default score based on response content
            return fallback_relevance_score(summary_response, test_query)
            
    except Exception as e:
        print(f"    ⚠️  LLM relevance analysis failed: {e}")
        # Fallback to keyword-based scoring
        return fallback_relevance_score(summary_response, test_query)

def fallback_relevance_score(summary_response, test_query):
    """Fallback relevance scoring using keyword matching when LLM analysis fails."""
    response_lower = summary_response.lower()
    query_lower = test_query['query'].lower()
    
    print(f"    🔄 Using fallback keyword-based scoring")
    
    # Extract key terms from the query
    query_terms = set()
    for word in query_lower.split():
        # Remove common stop words
        if word not in ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those']:
            if len(word) > 2:  # Only consider words longer than 2 characters
                query_terms.add(word)
    
    # Calculate score based on term overlap
    matching_terms = []
    for term in query_terms:
        if term in response_lower:
            matching_terms.append(term)
    
    # Calculate relevance score (0-10 scale)
    if len(query_terms) > 0:
        score = (len(matching_terms) / len(query_terms)) * 10
    else:
        score = 0.0
    
    # Bonus for explicit relevance indicators
    if 'yes' in response_lower and 'relevant' in response_lower:
        score += 2.0
    elif 'yes' in response_lower:
        score += 1.0
    elif 'no' in response_lower and 'not relevant' in response_lower:
        score -= 2.0
    elif 'no' in response_lower:
        score -= 1.0
    
    # Penalize very short responses
    if len(summary_response) < 20:
        score -= 1.0
    
    final_score = max(0.0, min(10.0, score))
    print(f"    🎯 Fallback score: {final_score:.1f} (matched: {len(matching_terms)}/{len(query_terms)} terms)")
    
    return final_score

def truncate_summary_for_synthesis(summary_text, max_length=500):
    """Truncate summary text to a reasonable length for LLM synthesis."""
    if len(summary_text) <= max_length:
        return summary_text
    
    # Try to truncate at a sentence boundary
    truncated = summary_text[:max_length]
    last_period = truncated.rfind('.')
    last_exclamation = truncated.rfind('!')
    last_question = truncated.rfind('?')
    
    # Find the last sentence ending
    last_sentence_end = max(last_period, last_exclamation, last_question)
    
    if last_sentence_end > max_length * 0.7:  # If we can find a good sentence break
        return truncated[:last_sentence_end + 1]
    else:
        # Just truncate and add ellipsis
        return truncated.rstrip() + "..."

def retrieve_comprehensive_document_information(doc_name, document_tools, test_query, storage_manager):
    """Retrieve comprehensive information from a document using multiple approaches."""
    try:
        doc_info = document_tools[doc_name]
        vector_tool = doc_info['vector_tool']
        
        # Approach 1: Multiple focused queries with different angles
        comprehensive_queries = [
            f"Find ALL information about: {test_query['query']}. Retrieve comprehensive details including exact numbers, years, tariff rates, fixed charges, discom names (MSEDCL, AEML, TATA), regulatory decisions, and any related information.",
            f"Extract complete tariff information, rates, charges, and regulatory decisions related to {test_query['query']}",
            f"Find detailed information about fixed charges, tariff rates, and pricing information for {test_query['query']}",
            f"Retrieve comprehensive regulatory information including all numbers, dates, and decisions about {test_query['query']}",
            f"What are the complete details and context about {test_query['query']}? Include all relevant regulatory information, decisions, and supporting data.",
            f"Extract ALL specific numbers, rates, charges, and financial information related to {test_query['query']}",
            f"Find complete regulatory decisions, approvals, and policy information about {test_query['query']}",
            f"Retrieve comprehensive information about discoms, utilities, and their tariff structures related to {test_query['query']}"
        ]
        
        all_responses = []
        
        for query in comprehensive_queries:
            try:
                response = vector_tool.fn(query=query, page_numbers=[])
                if len(response) > 50 and response not in all_responses:
                    all_responses.append(response)
            except Exception as e:
                print(f"    ⚠️  Query failed: {e}")
                continue
        
        # Approach 2: Extract key terms and query each
        query_terms = test_query['query'].lower().split()
        key_terms = [term for term in query_terms if len(term) > 3 and term not in ['the', 'and', 'for', 'are', 'with', 'this', 'that', 'have', 'been', 'from', 'they', 'will', 'would', 'could', 'should']]
        
        for term in key_terms[:5]:  # Use top 5 key terms
            try:
                term_query = f"Find detailed information about {term} in relation to {test_query['query']}. Include specific numbers, rates, and regulatory details."
                response = vector_tool.fn(query=term_query, page_numbers=[])
                if len(response) > 50 and response not in all_responses:
                    all_responses.append(response)
            except Exception as e:
                continue
        
        # Approach 3: Query for specific types of information
        specific_queries = [
            f"Find all tariff rates, charges, and pricing information in this document",
            f"Extract all regulatory decisions, orders, and approvals mentioned in this document",
            f"Find all specific numbers, percentages, and financial figures in this document",
            f"Retrieve all information about discoms, utilities, and their operations",
            f"Find all dates, years, and time periods mentioned in this document"
        ]
        
        for query in specific_queries:
            try:
                response = vector_tool.fn(query=query, page_numbers=[])
                if len(response) > 50 and response not in all_responses:
                    all_responses.append(response)
            except Exception as e:
                continue
        
        # Combine all responses with better organization
        if all_responses:
            # Remove duplicates while preserving order
            unique_responses = []
            seen_content = set()
            for response in all_responses:
                # Create a simple hash of the content to detect duplicates
                content_hash = hash(response[:200])  # Use first 200 chars as hash
                if content_hash not in seen_content:
                    unique_responses.append(response)
                    seen_content.add(content_hash)
            
            combined_response = f"\n\n=== COMPREHENSIVE INFORMATION FROM {doc_name} ===\n\n"
            combined_response += "\n\n--- SECTION ---\n\n".join(unique_responses)
            combined_response += f"\n\n=== END OF {doc_name} ===\n\n"
            return combined_response
        else:
            return f"No comprehensive information found in {doc_name}."
            
    except Exception as e:
        print(f"    ❌ Error in comprehensive retrieval for {doc_name}: {e}")
        return f"Error retrieving information from {doc_name}: {str(e)}"

@rate_limited(max_calls_per_minute=15)
def analyze_document_relevance(doc_name, summary_tool, test_query):
    """Analyze a single document for relevance (for parallel processing)."""
    try:
        print(f"    🔍 Analyzing document: {doc_name}")
        
        # Create a focused summary query based on the actual test query
        original_query = test_query['query']
        
        # Create a dynamic summary query that asks about the specific query content
        summary_query = f"Does this document contain information relevant to: '{original_query}'? Answer YES/NO and briefly explain why in 1-2 sentences."
        
        print(f"    📝 Summary query: {summary_query[:100]}...")
        
        try:
            summary_response = summary_tool.fn(query=summary_query)
            print(f"    📄 Summary response: {summary_response[:100]}...")
        except Exception as e:
            # If the summary tool fails, try with an even simpler query
            if "Input too long" in str(e) or "too long" in str(e).lower():
                print(f"    ⚠️  Summary tool failed for {doc_name}, trying simpler query...")
                try:
                    # Extract key terms from the original query for a simpler query
                    query_lower = original_query.lower()
                    key_terms = []
                    
                    # Extract important terms from the query
                    if any(term in query_lower for term in ['tariff', 'charge', 'rate', 'pricing']):
                        key_terms.append('tariff or pricing information')
                    if any(term in query_lower for term in ['msedcl', 'aeml', 'tata', 'discom']):
                        key_terms.append('discom information')
                    if any(term in query_lower for term in ['renewable', 'solar', 'wind', 'energy']):
                        key_terms.append('renewable energy information')
                    if any(term in query_lower for term in ['regulation', 'order', 'policy']):
                        key_terms.append('regulatory information')
                    
                    if key_terms:
                        simple_query = f"Does this document contain {' or '.join(key_terms)}? YES/NO only."
                    else:
                        simple_query = "Does this document contain relevant regulatory information? YES/NO only."
                    
                    summary_response = summary_tool.fn(query=simple_query)
                    print(f"    📄 Simple summary response: {summary_response[:100]}...")
                except Exception as e2:
                    # If still failing, use document name analysis
                    print(f"    ⚠️  Summary tool still failing for {doc_name}, using document name analysis...")
                    doc_lower = doc_name.lower()
                    
                    # Analyze document name for relevance based on the actual query
                    query_lower = original_query.lower()
                    relevance_indicators = []
                    
                    # Add indicators based on the actual query content
                    if any(term in query_lower for term in ['tariff', 'charge', 'rate']):
                        relevance_indicators.extend(['tariff', 'charge', 'order', 'rate'])
                    if any(term in query_lower for term in ['msedcl', 'aeml', 'tata', 'discom']):
                        relevance_indicators.extend(['msedcl', 'aeml', 'tata', 'discom'])
                    if any(term in query_lower for term in ['renewable', 'solar', 'wind']):
                        relevance_indicators.extend(['re', 'renewable', 'solar', 'wind'])
                    if any(term in query_lower for term in ['regulation', 'order', 'policy']):
                        relevance_indicators.extend(['regulation', 'order', 'merc'])
                    
                    # If no specific indicators found, use general ones
                    if not relevance_indicators:
                        relevance_indicators = ['tariff', 'charge', 'order', 'regulation', 'merc']
                    
                    relevance_count = sum(1 for indicator in relevance_indicators if indicator in doc_lower)
                    
                    if relevance_count >= 2:
                        summary_response = f"YES - Document name suggests content relevant to the query about {', '.join(relevance_indicators[:2])}."
                    elif relevance_count >= 1:
                        summary_response = f"MAYBE - Document name has some terms relevant to the query."
                    else:
                        summary_response = "NO - Document name doesn't suggest relevant content."
                    
                    print(f"    📄 Document name analysis response: {summary_response}")
            else:
                raise e
        
        # Truncate the summary response to prevent input length issues
        truncated_response = truncate_summary_for_synthesis(summary_response, max_length=500)
        
        # Calculate relevance score using the new LLM-based approach
        print(f"    🎯 Calculating relevance score for: {truncated_response[:50]}...")
        relevance_score = calculate_document_relevance(truncated_response, test_query)
        
        print(f"    ✅ Final relevance score for {doc_name}: {relevance_score:.1f}")
        
        return {
            'doc_name': doc_name,
            'relevance_score': relevance_score,
            'summary_response': truncated_response
        }
        
    except Exception as e:
        print(f"    ❌ Error analyzing {doc_name}: {e}")
        return {
            'doc_name': doc_name,
            'relevance_score': 0.0,
            'summary_response': f"Error: {str(e)}"
        }

def get_user_query():
    """Get a custom query from the user."""
    print(f"\n{'='*60}")
    print("🔍 Custom Query Input")
    print(f"{'='*60}")
    
    print("Enter your query below. Examples:")
    print("  - How have tariffs like Fixed charges changed over time in MSEDCL, AEML, TATA, etc?")
    print("  - What are the renewable energy tariff rates for solar and wind projects?")
    print("  - Find information about demand charges and their evolution over the years")
    print("  - What does the regulatory framework say about cross-subsidy surcharges?")
    
    # Ask for processing mode
    print(f"\n⚡ Processing Mode:")
    print("  'fast' - Quick analysis (top 10 documents, faster)")
    print("  'comprehensive' - Full analysis (all documents, slower)")
    
    while True:
        mode_choice = input("\nChoose processing mode (fast/comprehensive): ").strip().lower()
        if mode_choice in ['fast', 'comprehensive']:
            break
        else:
            print("Please choose 'fast' or 'comprehensive'")
    
    while True:
        user_query = input("\nEnter your query (or 'default' for sample query): ").strip()
        
        if not user_query:
            print("Please enter a query.")
            continue
        
        if user_query.lower() == 'default':
            return {
                "name": "Tariff Search",
                "query": "Fixed charges for LT and HT for MSEDCL for FY 25-26",
                "description": "Multi-document tariff analysis with specific numbers and discom details",
                "mode": mode_choice
            }
        
        # Validate query length
        if len(user_query) < 10:
            print("Query too short. Please provide more detail.")
            continue
        
        if len(user_query) > 500:
            print("Query too long. Please be more concise.")
            continue
        
        # Confirm the query
        print(f"\n📝 Your query: {user_query}")
        print(f"⚡ Processing mode: {mode_choice}")
        confirm = input("Is this correct? (y/n): ").strip().lower()
        
        if confirm in ['y', 'yes']:
            return {
                "name": "Custom Query",
                "query": user_query,
                "description": "User-defined query for regulatory document analysis",
                "mode": mode_choice
            }
        else:
            print("Please re-enter your query.")

def run_query_session(selected_docs, document_tools):
    """Run an interactive query session allowing multiple queries."""
    print(f"\n🚀 Starting Interactive Query Session")
    print(f"Documents available: {len(selected_docs)}")
    print(f"Type 'quit' to exit the session")
    
    query_count = 0
    
    while True:
        query_count += 1
        print(f"\n{'='*60}")
        print(f"Query #{query_count}")
        print(f"{'='*60}")
        
        # Ask if user wants to continue
        if query_count > 1:
            continue_query = input("\nRun another query? (y/n): ").strip().lower()
            if continue_query not in ['y', 'yes']:
                print("Ending query session.")
                break
        
        # Run the query
        query_documents(selected_docs, document_tools)
        
        # Show session summary
        print(f"\n📊 Query Session Summary")
        print(f"  Queries completed: {query_count}")
        print(f"  Documents available: {len(selected_docs)}")
        print(f"  Tools loaded: {len(selected_docs) * 2}")

def main():
    """Main function to run the multi-document query system."""
    print("🚀 Multi-Document Regulatory Query System")
    print("=" * 50)
    
    # Configuration for document filtering
    exclude_keywords = get_exclude_keywords()
    
    # Preview document filtering
    preview_document_filtering(exclude_keywords)
    
    # Load all document tools using cache with filtering
    document_tools = load_all_document_tools(exclude_keywords=exclude_keywords)
    
    if not document_tools:
        print("No documents available for querying!")
        return
    
    # HARD FILTER: Remove specific documents that should never be included
    hard_exclude_docs = []
    for doc_name in list(document_tools.keys()):
        doc_lower = doc_name.lower()
        if 'manjari' in doc_lower or 'hadapsar' in doc_lower:
            hard_exclude_docs.append(doc_name)
            document_tools.pop(doc_name)
    
    if hard_exclude_docs:
        print(f"\n🚫 HARD FILTER: Removed {len(hard_exclude_docs)} documents:")
        for doc in hard_exclude_docs:
            print(f"   ❌ {doc}")
        print(f"   Remaining documents: {len(document_tools)}")
    
    # If exclude keywords were used, offer to force rebuild to ensure clean filtering
    if exclude_keywords:
        print(f"\n🔧 Filtering Options:")
        print(f"   Exclude keywords: {', '.join(exclude_keywords)}")
        print(f"   Documents loaded: {len(document_tools)}")
        
        rebuild_choice = input("\nForce rebuild tools to ensure clean filtering? (y/n): ").strip().lower()
        if rebuild_choice in ['y', 'yes']:
            print(f"\n🔄 Force rebuilding tools with filtering...")
            document_tools = load_all_document_tools(force_rebuild=True, exclude_keywords=exclude_keywords)
            if not document_tools:
                print("No documents available after force rebuild!")
                return
            
            # Apply hard filter again after rebuild
            hard_exclude_docs = []
            for doc_name in list(document_tools.keys()):
                doc_lower = doc_name.lower()
                if 'manjari' in doc_lower or 'hadapsar' in doc_lower:
                    hard_exclude_docs.append(doc_name)
                    document_tools.pop(doc_name)
            
            if hard_exclude_docs:
                print(f"\n🚫 HARD FILTER: Removed {len(hard_exclude_docs)} documents after rebuild:")
                for doc in hard_exclude_docs:
                    print(f"   ❌ {doc}")
                print(f"   Final document count: {len(document_tools)}")
    
    # Select documents to query (use all available)
    selected_docs = list(document_tools.keys())
    
    if not selected_docs:
        print("No documents selected!")
        return
    
    # Run the interactive query session
    run_query_session(selected_docs, document_tools)
    
    # Display final statistics
    print(f"\n{'='*60}")
    print("📊 Session Summary")
    print(f"{'='*60}")
    print(f"Total indexed documents: {len(document_tools)}")
    print(f"Documents queried: {len(selected_docs)}")
    print(f"Tools used: {len(selected_docs) * 2} (vector + summary per document)")
    
    # Show cache statistics
    cache_stats = tool_cache.get_cache_stats()
    print(f"\n--- Cache Information ---")
    print(f"Total cached documents: {cache_stats['total_cached_documents']}")
    print(f"Memory cache size: {cache_stats['memory_cache_size']}")
    
    # Show storage information
    print(f"\n--- Storage Information ---")
    all_documents = storage_manager.list_documents()
    print(f"Total stored documents: {len(all_documents)}")
    
    # Show some example documents
    if all_documents:
        print(f"Sample documents: {', '.join(all_documents[:5])}{'...' if len(all_documents) > 5 else ''}")

if __name__ == "__main__":
    main()



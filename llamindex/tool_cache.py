import os
import json
import pickle
import hashlib
from typing import Dict, List, Optional
from pathlib import Path
import re

from llama_index.core.tools import FunctionTool
from storage_manager import StorageManager
from ingestion import extract_nodes_from_pdf


def get_tool_description(tool, default_description=""):
    """Safely get tool description with fallback."""
    try:
        # Try different ways to access description
        if hasattr(tool, 'description'):
            return tool.description
        elif hasattr(tool, '_description'):
            return tool._description
        elif hasattr(tool, 'metadata') and 'description' in tool.metadata:
            return tool.metadata['description']
        else:
            return default_description
    except:
        return default_description


def create_unique_tools(nodes, document_name, storage_manager, use_chroma=True):
    """Create tools with unique names for each document."""
    from vector_tool_factory import create_vector_query_tool
    from summary_tool_factory import create_summary_tool
    
    # Create tools with unique names
    vector_tool = create_vector_query_tool(
        nodes=nodes,
        document_name=document_name,
        storage_manager=storage_manager,
        use_chroma=use_chroma,
    )
    
    summary_tool = create_summary_tool(
        nodes=nodes,
        document_name=document_name,
        storage_manager=storage_manager,
        use_chroma=use_chroma,
    )
    
    # Create a unique identifier for the document name
    # Sanitize the name to only allow alphanumeric, underscore, and hyphen
    # Replace all other characters with underscore
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', document_name)
    # Remove consecutive underscores and limit length
    safe_name = re.sub(r'_+', '_', safe_name)[:20]
    # Ensure it doesn't start with a number
    if safe_name and safe_name[0].isdigit():
        safe_name = 'doc_' + safe_name
    
    name_hash = hashlib.md5(document_name.encode()).hexdigest()[:8]
    unique_id = f"{safe_name}_{name_hash}"
    
    # Clone tools with unique names
    from llama_index.core.tools import FunctionTool
    
    # Get descriptions safely
    vector_description = get_tool_description(
        vector_tool, 
        f"Search for information in the document '{document_name}'. Use simple, single-word or short phrase queries like 'tariff', 'solar', 'wind', 'pricing', 'charges', 'renewable energy'. Do NOT use complex or technical phrases. Keep queries under 3 words for best results. IMPORTANT: Do NOT specify page_numbers - leave it empty or use [] to search all pages."
    )
    summary_description = get_tool_description(
        summary_tool,
        f"Get a comprehensive summary of the document '{document_name}'. Use queries like 'summarize this document', 'what are the main points', 'give me an overview'. This tool provides high-level summaries of the entire document."
    )
    
    # Create unique vector tool
    unique_vector_tool = FunctionTool.from_defaults(
        name=f"regulatory_search_tool_{unique_id}",
        fn=vector_tool.fn,
        description=f"Vector search tool for document: {document_name}. {vector_description}"
    )
    
    # Create unique summary tool
    unique_summary_tool = FunctionTool.from_defaults(
        name=f"regulatory_summary_tool_{unique_id}",
        fn=summary_tool.fn,
        description=f"Summary tool for document: {document_name}. {summary_description}"
    )
    
    return unique_vector_tool, unique_summary_tool


class ToolCache:
    """
    Cache for document tools to avoid recreating them on every query.
    """
    
    def __init__(self, storage_manager: StorageManager, cache_dir: str = "./tool_cache"):
        self.storage_manager = storage_manager
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._tools_cache = {}
        self._metadata_cache = {}
    
    def _get_cache_key(self, document_name: str) -> str:
        """Generate cache key for a document."""
        return f"{document_name}_tools.pkl"
    
    def _get_metadata_key(self, document_name: str) -> str:
        """Generate metadata cache key for a document."""
        return f"{document_name}_metadata.json"
    
    def _is_cache_valid(self, document_name: str) -> bool:
        """Check if cached tools are still valid."""
        cache_file = self.cache_dir / self._get_cache_key(document_name)
        metadata_file = self.cache_dir / self._get_metadata_key(document_name)
        
        if not cache_file.exists() or not metadata_file.exists():
            return False
        
        try:
            # Check if document metadata has changed
            current_metadata = self.storage_manager.get_document_metadata(document_name)
            with open(metadata_file, 'r') as f:
                cached_metadata = json.load(f)
            
            # Compare key metadata fields
            current_hash = hash(str(current_metadata.get('vector_index', {})) + str(current_metadata.get('summary_index', {})))
            cached_hash = cached_metadata.get('metadata_hash')
            
            return current_hash == cached_hash
            
        except Exception:
            return False
    
    def _save_tools_to_cache(self, document_name: str, tools: Dict, metadata: Dict):
        """Save tools to cache."""
        try:
            # Save tools
            cache_file = self.cache_dir / self._get_cache_key(document_name)
            with open(cache_file, 'wb') as f:
                pickle.dump(tools, f)
            
            # Save metadata with hash
            metadata_file = self.cache_dir / self._get_metadata_key(document_name)
            current_metadata = self.storage_manager.get_document_metadata(document_name)
            metadata_hash = hash(str(current_metadata.get('vector_index', {})) + str(current_metadata.get('summary_index', {})))
            
            cache_metadata = {
                'document_name': document_name,
                'metadata_hash': metadata_hash,
                'node_count': metadata.get('node_count', 0),
                'cached_at': str(Path(cache_file).stat().st_mtime)
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(cache_metadata, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save tools to cache for {document_name}: {e}")
    
    def _load_tools_from_cache(self, document_name: str) -> Optional[Dict]:
        """Load tools from cache."""
        try:
            cache_file = self.cache_dir / self._get_cache_key(document_name)
            with open(cache_file, 'rb') as f:
                tools = pickle.load(f)
            return tools
        except Exception as e:
            print(f"Warning: Could not load tools from cache for {document_name}: {e}")
            return None
    
    def get_tools_for_document(self, document_name: str, force_rebuild: bool = False):
        """
        Get tools for a document, using cache if available.
        
        Args:
            document_name: Name of the document
            force_rebuild: Force rebuild tools even if cache exists
            
        Returns:
            Dict with 'vector_tool', 'summary_tool', 'node_count', 'metadata'
        """
        # Check if already in memory cache
        if document_name in self._tools_cache and not force_rebuild:
            print(f"  📦 Using memory cache for {document_name}")
            result = self._tools_cache[document_name]
            result['metadata']['cached'] = True
            return result
        
        # Check if valid cache exists on disk
        if not force_rebuild and self._is_cache_valid(document_name):
            cached_tools = self._load_tools_from_cache(document_name)
            if cached_tools:
                print(f"  📦 Using disk cache for {document_name}")
                self._tools_cache[document_name] = cached_tools
                cached_tools['metadata']['cached'] = True
                return cached_tools
        
        # Build tools from scratch
        print(f"  🔨 Building tools for {document_name} (no cache available)...")
        
        # Load nodes
        nodes = self.storage_manager.load_nodes(document_name)
        if not nodes:
            raise ValueError(f"No nodes found for document: {document_name}")
        
        # Create tools using the local function
        vector_tool, summary_tool = create_unique_tools(
            nodes=nodes,
            document_name=document_name,
            storage_manager=self.storage_manager,
            use_chroma=True
        )
        
        # Prepare result
        result = {
            'vector_tool': vector_tool,
            'summary_tool': summary_tool,
            'node_count': len(nodes),
            'metadata': self.storage_manager.get_document_metadata(document_name)
        }
        result['metadata']['cached'] = False
        
        # Save to cache
        self._save_tools_to_cache(document_name, result, result)
        
        # Store in memory cache
        self._tools_cache[document_name] = result
        
        return result
    
    def get_tools_for_documents(self, document_names: List[str], force_rebuild: bool = False) -> Dict[str, Dict]:
        """
        Get tools for multiple documents.
        
        Args:
            document_names: List of document names
            force_rebuild: Force rebuild tools even if cache exists
            
        Returns:
            Dict mapping document_name to tools dict
        """
        results = {}
        total_docs = len(document_names)
        cache_hits = 0
        new_builds = 0
        errors = 0
        
        print(f"\n🔄 Processing {total_docs} documents...")
        
        for i, doc_name in enumerate(document_names, 1):
            try:
                print(f"\n[{i}/{total_docs}] Processing: {doc_name}")
                results[doc_name] = self.get_tools_for_document(doc_name, force_rebuild)
                
                # Track statistics
                if results[doc_name]['metadata'].get('cached', False):
                    cache_hits += 1
                else:
                    new_builds += 1
                
                print(f"  ✅ Loaded {results[doc_name]['node_count']} nodes")
                print(f"  📊 Progress: {i}/{total_docs} ({i/total_docs*100:.1f}%) - Cache hits: {cache_hits}, New builds: {new_builds}, Errors: {errors}")
                
            except Exception as e:
                errors += 1
                print(f"  ❌ Error loading {doc_name}: {e}")
                print(f"  📊 Progress: {i}/{total_docs} ({i/total_docs*100:.1f}%) - Cache hits: {cache_hits}, New builds: {new_builds}, Errors: {errors}")
                continue
        
        print(f"\n📊 Final Processing Summary:")
        print(f"  Total documents: {total_docs}")
        print(f"  Cache hits: {cache_hits}")
        print(f"  New builds: {new_builds}")
        print(f"  Errors: {errors}")
        print(f"  Success rate: {((total_docs-errors)/total_docs*100):.1f}%")
        
        return results
    
    def clear_cache(self, document_name: Optional[str] = None):
        """
        Clear cache for specific document or all documents.
        
        Args:
            document_name: If provided, clear only this document's cache. If None, clear all.
        """
        if document_name:
            # Clear specific document
            cache_file = self.cache_dir / self._get_cache_key(document_name)
            metadata_file = self.cache_dir / self._get_metadata_key(document_name)
            
            if cache_file.exists():
                cache_file.unlink()
            if metadata_file.exists():
                metadata_file.unlink()
            
            # Remove from memory cache
            self._tools_cache.pop(document_name, None)
            print(f"Cleared cache for {document_name}")
        else:
            # Clear all cache
            for file in self.cache_dir.glob("*"):
                file.unlink()
            self._tools_cache.clear()
            print("Cleared all tool cache")
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about the cache."""
        cache_files = list(self.cache_dir.glob("*_tools.pkl"))
        metadata_files = list(self.cache_dir.glob("*_metadata.json"))
        
        cached_documents = []
        for metadata_file in metadata_files:
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    cached_documents.append({
                        'document_name': metadata.get('document_name'),
                        'node_count': metadata.get('node_count', 0),
                        'cached_at': metadata.get('cached_at')
                    })
            except Exception:
                continue
        
        return {
            'cache_dir': str(self.cache_dir),
            'total_cached_documents': len(cached_documents),
            'memory_cache_size': len(self._tools_cache),
            'cached_documents': cached_documents
        } 
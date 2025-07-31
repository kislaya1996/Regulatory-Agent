import os
import json
import pickle
from typing import List, Optional, Dict, Any
from pathlib import Path
from llama_index.core import VectorStoreIndex, DocumentSummaryIndex, SummaryIndex
from llama_index.core.schema import BaseNode
from llama_index.core.storage import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.vector_stores import SimpleVectorStore # Potentially needed for file-based loading if it's implicitly used
import chromadb
from llama_index.core import Settings

# Import our custom embedding model
try:
    from embedding_model import embed_model
except ImportError:
    embed_model = None
    print("Warning: embedding_model not found. Ensure Settings.embed_model is configured.")


class StorageManager:
    """
    Manages persistence and storage for nodes and indexes in the regulatory tracker.
    Supports both file-based storage and vector store persistence.
    """
    
    def __init__(self, base_dir: str = "./storage"):
        self.base_dir = Path(base_dir)
        self.nodes_dir = self.base_dir / "nodes"
        self.vector_indexes_dir = self.base_dir / "vector_indexes" # Directory for VectorStoreIndex metadata
        self.summary_indexes_dir = self.base_dir / "summary_indexes" # Directory for DocumentSummaryIndex metadata
        self.metadata_dir = self.base_dir / "metadata"
        self.chroma_dir = self.base_dir / "chroma_db" # Where ChromaDB stores its actual database files
        
        # Create directories if they don't exist
        self.nodes_dir.mkdir(parents=True, exist_ok=True)
        self.vector_indexes_dir.mkdir(parents=True, exist_ok=True)
        self.summary_indexes_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
    
    def save_nodes(self, nodes: List[BaseNode], document_name: str) -> str:
        """
        Save processed nodes to disk using pickle.
        
        Args:
            nodes: List of processed nodes
            document_name: Name identifier for the document
            
        Returns:
            Path to the saved nodes file
        """
        nodes_file = self.nodes_dir / f"{document_name}_nodes.pkl"
        
        with open(nodes_file, 'wb') as f:
            pickle.dump(nodes, f)
        
        print(f"Saved {len(nodes)} nodes to {nodes_file}")
        return str(nodes_file)
    
    def load_nodes(self, document_name: str) -> Optional[List[BaseNode]]:
        """
        Load processed nodes from disk.
        
        Args:
            document_name: Name identifier for the document
            
        Returns:
            List of nodes if found, None otherwise
        """
        nodes_file = self.nodes_dir / f"{document_name}_nodes.pkl"
        
        if not nodes_file.exists():
            print(f"No saved nodes found for {document_name}")
            return None
        
        try:
            with open(nodes_file, 'rb') as f:
                nodes = pickle.load(f)
            print(f"Loaded {len(nodes)} nodes from {nodes_file}")
            return nodes
        except Exception as e:
            print(f"Error loading nodes: {e}")
            return None
    
    def save_vector_index(self, index: VectorStoreIndex, document_name: str, 
                         use_chroma: bool = True) -> str:
        """
        Save vector index with persistence.
        
        Args:
            index: VectorStoreIndex to save
            document_name: Name identifier for the document
            use_chroma: Whether the index uses ChromaDB (for metadata logging)
            
        Returns:
            Path to the saved index metadata directory
        """
        # This persists LlamaIndex's internal docstore/indexstore metadata
        # The persist_dir should be where the index's storage_context was told to persist
        # which is `self.vector_indexes_dir / document_name` or `self.vector_indexes_dir / f"{document_name}_file_based"`
        
        # Determine the correct persist_dir used during index creation
        index_persist_dir = self.vector_indexes_dir / document_name if use_chroma else \
                            self.vector_indexes_dir / f"{document_name}_file_based"
        
        index.storage_context.persist(persist_dir=str(index_persist_dir))
        
        # Save metadata specifically for the vector index
        metadata = {
            "document_name": document_name,
            "index_type": "vector",
            "storage_type": "chroma" if use_chroma else "file", # Reflect storage type
            "collection_name": f"{document_name}_collection" if use_chroma else None, # Chroma collection name
            "node_count": len(index.docstore.docs), # Number of nodes in the document store
            "created_at": str(os.path.getmtime(index_persist_dir)) # Timestamp of LlamaIndex metadata persistence
        }
        
        metadata_file = self.metadata_dir / f"{document_name}_vector_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Saved vector index metadata to {index_persist_dir}")
        return str(index_persist_dir)
    
    def load_vector_index(self, document_name: str, use_chroma: bool = True) -> Optional[VectorStoreIndex]:
        """
        Load vector index from storage.
        
        Args:
            document_name: Name identifier for the document
            use_chroma: Whether to use ChromaDB for loading
            
        Returns:
            VectorStoreIndex if found, None otherwise
        """
        # Determine the expected persist_dir for LlamaIndex's internal metadata
        vector_index_persist_dir = self.vector_indexes_dir / document_name if use_chroma else \
                                    self.vector_indexes_dir / f"{document_name}_file_based"

        if not vector_index_persist_dir.exists():
            print(f"No saved vector index metadata found for {document_name} at {vector_index_persist_dir}")
            return None
        
        try:
            # Load metadata to determine the actual storage type and collection name
            metadata_file = self.metadata_dir / f"{document_name}_vector_metadata.json"
            if not metadata_file.exists():
                print(f"No vector metadata found for {document_name}")
                return None
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            if use_chroma and metadata.get("storage_type") == "chroma":
                chroma_collection_name = metadata.get("collection_name", f"{document_name}_collection")
                chroma_client = chromadb.PersistentClient(path=str(self.chroma_dir))
                
                try:
                    collection = chroma_client.get_collection(name=chroma_collection_name)
                    
                    vector_store = ChromaVectorStore(chroma_collection=collection)
                    
                    # Recreate StorageContext with the ChromaVectorStore and the persist_dir
                    storage_context = StorageContext.from_defaults(
                        vector_store=vector_store,
                        persist_dir=str(vector_index_persist_dir) # Point to LlamaIndex's internal metadata
                    )
                    
                    if embed_model:
                        Settings.embed_model = embed_model

                    index = VectorStoreIndex.from_vector_store(vector_store)
                    
                    print(f"Loaded vector index from {vector_index_persist_dir} using ChromaDB collection: {chroma_collection_name}")
                    return index
                    
                except Exception as e:
                    print(f"Error loading vector index from ChromaDB collection {chroma_collection_name}: {e}")
                    # Fallback to recreate if ChromaDB collection cannot be loaded for some reason
                    nodes = self.load_nodes(document_name)
                    if nodes:
                        print(f"Attempting to recreate vector index for {document_name} from stored nodes.")
                        try:
                            # Re-initialize ChromaDB for recreation
                            recreate_db = chromadb.PersistentClient(path=str(self.chroma_dir))
                            recreate_collection = recreate_db.get_or_create_collection(chroma_collection_name)
                            recreate_vector_store = ChromaVectorStore(chroma_collection=recreate_collection)
                            recreate_storage_context = StorageContext.from_defaults(
                                vector_store=recreate_vector_store,
                                persist_dir=str(vector_index_persist_dir)
                            )
                            if embed_model:
                                Settings.embed_model = embed_model
                            index = VectorStoreIndex(
                                nodes,
                                storage_context=recreate_storage_context
                            )
                            # Persist the newly recreated index metadata
                            index.storage_context.persist(persist_dir=str(vector_index_persist_dir))
                            print(f"Recreated vector index from nodes for {document_name}.")
                            return index
                        except Exception as recreate_e:
                            print(f"Failed to recreate vector index from nodes: {recreate_e}")
                            return None
                    else:
                        print(f"No stored nodes found to recreate vector index for {document_name}.")
                        return None
            elif not use_chroma and metadata.get("storage_type") == "file":
                # Handle file-based loading if you intend to support it
                storage_context = StorageContext.from_defaults(persist_dir=str(vector_index_persist_dir))
                if embed_model:
                    Settings.embed_model = embed_model
                index = VectorStoreIndex(storage_context=storage_context)
                print(f"Loaded file-based vector index from {vector_index_persist_dir}")
                return index
            else:
                print(f"Mismatch in storage type for {document_name}. Expected chroma={use_chroma}, found {metadata.get('storage_type')}.")
                return None
            
        except Exception as e:
            print(f"Error loading vector index (general error): {e}")
            return None
    
    def save_document_summary_index(self, index: SummaryIndex, document_name: str, use_chroma: bool = True) -> str:
        """
        Save document summary index to disk.
        
        Args:
            index: SummaryIndex to save
            document_name: Name identifier for the document
            use_chroma: Whether the index is using ChromaDB (for metadata logging)
            
        Returns:
            Path to the saved index metadata directory
        """
        # This persists LlamaIndex's internal docstore/indexstore metadata
        index_dir = self.summary_indexes_dir / document_name
        index.storage_context.persist(persist_dir=str(index_dir))
        
        # Save metadata specifically for the summary index
        metadata = {
            "document_name": document_name,
            "index_type": "summary",
            "storage_type": "chroma" if use_chroma else "file", # Reflect storage type
            "collection_name": f"{document_name}_summary" if use_chroma else None, # Chroma collection name
            "node_count": len(index.docstore.docs), # Number of nodes in the document store
            "created_at": str(os.path.getmtime(index_dir)) # Timestamp of LlamaIndex metadata persistence
        }
        
        metadata_file = self.metadata_dir / f"{document_name}_summary_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Saved document summary index metadata to {index_dir}")
        return str(index_dir)
    
    def load_document_summary_index(self, document_name: str, use_chroma: bool = True) -> Optional[SummaryIndex]:
        """
        Load document summary index from disk.
        
        Args:
            document_name: Name identifier for the document
            use_chroma: Whether the index uses ChromaDB for its vectors
            
        Returns:
            SummaryIndex if found, None otherwise
        """
        index_dir = self.summary_indexes_dir / document_name
        
        if not index_dir.exists():
            print(f"No saved document summary index metadata found for {document_name} at {index_dir}")
            return None
        
        try:
            # Load metadata to determine the ChromaDB collection name
            metadata_file = self.metadata_dir / f"{document_name}_summary_metadata.json"
            if not metadata_file.exists():
                print(f"No summary metadata found for {document_name}")
                return None
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

            if use_chroma and metadata.get("storage_type") == "chroma":
                chroma_collection_name = metadata.get("collection_name", f"{document_name}_summary")
                chroma_client = chromadb.PersistentClient(path=str(self.chroma_dir))
                
                try:
                    collection = chroma_client.get_collection(name=chroma_collection_name)
                    vector_store = ChromaVectorStore(chroma_collection=collection)
                    
                    # Create StorageContext with the ChromaVectorStore and persist_dir
                    storage_context = StorageContext.from_defaults(
                        vector_store=vector_store,
                        persist_dir=str(index_dir)
                    )
                    
                    if embed_model:
                        Settings.embed_model = embed_model
                    
                    # Try to load the existing index from storage first
                    try:
                        # Load the index structure from the storage context
                        from llama_index.core.indices.loading import load_index_from_storage
                        index = load_index_from_storage(storage_context)
                        print(f"Loaded existing document summary index from {index_dir} using ChromaDB collection: {chroma_collection_name}")
                        return index
                    except Exception as load_error:
                        print(f"Could not load existing SummaryIndex from storage: {load_error}")
                        print("Falling back to recreation from stored nodes...")
                        
                        # Fallback to recreation from nodes
                        nodes = self.load_nodes(document_name)
                        if not nodes:
                            print(f"No stored nodes found to recreate summary index for {document_name}.")
                            return None
                        
                        print(f"Recreating summary index for {document_name} from stored nodes.")
                        
                        # Recreate the SummaryIndex from nodes
                        index = SummaryIndex(
                            nodes,
                            storage_context=storage_context
                        )
                        
                        # Persist the newly recreated index metadata
                        index.storage_context.persist(persist_dir=str(index_dir))
                        print(f"Recreated summary index from nodes for {document_name} using ChromaDB collection: {chroma_collection_name}")
                        return index
                    
                except Exception as e:
                    print(f"Error with ChromaDB collection {chroma_collection_name}: {e}")
                    return None
                    
            elif not use_chroma and metadata.get("storage_type") == "file":
                # Handle file-based loading
                storage_context = StorageContext.from_defaults(persist_dir=str(index_dir))
                if embed_model:
                    Settings.embed_model = embed_model
                
                try:
                    # Try to load the existing index from storage first
                    from llama_index.core.indices.loading import load_index_from_storage
                    index = load_index_from_storage(storage_context)
                    print(f"Loaded existing file-based document summary index from {index_dir}")
                    return index
                except Exception as load_error:
                    print(f"Could not load existing file-based SummaryIndex from storage: {load_error}")
                    print("Falling back to recreation from stored nodes...")
                    
                    # Fallback to recreation from nodes
                    nodes = self.load_nodes(document_name)
                    if not nodes:
                        print(f"No stored nodes found to recreate summary index for {document_name}.")
                        return None
                    
                    print(f"Recreating file-based summary index for {document_name} from stored nodes.")
                    
                    index = SummaryIndex(
                        nodes,
                        storage_context=storage_context
                    )
                    
                    # Persist the newly recreated index metadata
                    index.storage_context.persist(persist_dir=str(index_dir))
                    print(f"Recreated file-based summary index from nodes for {document_name}")
                    return index
            else:
                print(f"Mismatch in storage type for {document_name}. Expected chroma={use_chroma}, found {metadata.get('storage_type')}.")
                return None
            
        except Exception as e:
            print(f"Error loading document summary index (general error): {e}")
            return None
    
    def get_document_metadata(self, document_name: str) -> Dict[str, Any]:
        """
        Get metadata for a document.
        
        Args:
            document_name: Name identifier for the document
            
        Returns:
            Dictionary containing metadata for both vector indexes (search and summary)
        """
        metadata = {}
        
        # Check for vector index metadata (for search)
        vector_metadata_file = self.metadata_dir / f"{document_name}_vector_metadata.json"
        if vector_metadata_file.exists():
            with open(vector_metadata_file, 'r') as f:
                metadata['vector_index'] = json.load(f)
        
        # Check for summary index metadata (for summary tool)
        summary_metadata_file = self.metadata_dir / f"{document_name}_summary_metadata.json"
        if summary_metadata_file.exists():
            with open(summary_metadata_file, 'r') as f:
                metadata['summary_index'] = json.load(f)
        
        # Check for nodes
        nodes_file = self.nodes_dir / f"{document_name}_nodes.pkl"
        if nodes_file.exists():
            metadata['nodes'] = {
                "file_path": str(nodes_file),
                "exists": True
            }
        else:
            metadata['nodes'] = {
                "exists": False
            }
        
        return metadata
    
    def list_documents(self) -> List[str]:
        """
        List all documents that have been processed and stored.
        
        Returns:
            List of document names
        """
        documents = set()
        
        # Check nodes directory
        for file in self.nodes_dir.glob("*_nodes.pkl"):
            doc_name = file.stem.replace("_nodes", "")
            documents.add(doc_name)
        
        # Check metadata directory
        for file in self.metadata_dir.glob("*_metadata.json"):
            doc_name = file.stem.replace("_vector_metadata", "").replace("_summary_metadata", "")
            documents.add(doc_name)
        
        return sorted(list(documents))
    
    def delete_document(self, document_name: str) -> bool:
        """
        Delete all stored data for a document.
        
        Args:
            document_name: Name identifier for the document
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Delete nodes
            nodes_file = self.nodes_dir / f"{document_name}_nodes.pkl"
            if nodes_file.exists():
                nodes_file.unlink()
            
            # Delete vector index metadata directory (Chroma-based)
            vector_index_chroma_dir = self.vector_indexes_dir / document_name
            if vector_index_chroma_dir.exists():
                import shutil
                shutil.rmtree(vector_index_chroma_dir)

            # Delete vector index metadata directory (File-based fallback)
            vector_index_file_dir = self.vector_indexes_dir / f"{document_name}_file_based"
            if vector_index_file_dir.exists():
                import shutil
                shutil.rmtree(vector_index_file_dir)
            
            # Delete summary index metadata directory
            summary_index_dir = self.summary_indexes_dir / document_name
            if summary_index_dir.exists():
                import shutil
                shutil.rmtree(summary_index_dir)
            
            # Delete metadata files
            vector_metadata_file = self.metadata_dir / f"{document_name}_vector_metadata.json"
            if vector_metadata_file.exists():
                vector_metadata_file.unlink()
            
            summary_metadata_file = self.metadata_dir / f"{document_name}_summary_metadata.json"
            if summary_metadata_file.exists():
                summary_metadata_file.unlink()
            
            # Delete ChromaDB collections if they exist
            chroma_client = chromadb.PersistentClient(path=str(self.chroma_dir))
            
            # Main vector collection
            try:
                chroma_collection_name_vector = f"{document_name}_collection"
                chroma_client.delete_collection(name=chroma_collection_name_vector)
                print(f"Deleted ChromaDB collection: {chroma_collection_name_vector}")
            except Exception as e:
                # print(f"ChromaDB collection {chroma_collection_name_vector} not found or error deleting: {e}")
                pass 
            
            # Summary vector collection
            try:
                chroma_collection_name_summary = f"{document_name}_summary"
                chroma_client.delete_collection(name=chroma_collection_name_summary)
                print(f"Deleted ChromaDB collection: {chroma_collection_name_summary}")
            except Exception as e:
                # print(f"ChromaDB collection {chroma_collection_name_summary} not found or error deleting: {e}")
                pass 
            
            print(f"Successfully deleted all data for document: {document_name}")
            return True
            
        except Exception as e:
            print(f"Error deleting document {document_name}: {e}")
            return False
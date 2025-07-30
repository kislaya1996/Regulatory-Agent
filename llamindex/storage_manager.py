import os
import json
import pickle
from typing import List, Optional, Dict, Any
from pathlib import Path
from llama_index.core import VectorStoreIndex, SummaryIndex
from llama_index.core.schema import BaseNode
from llama_index.core.storage import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.vector_stores import SimpleVectorStore
import chromadb
from llama_index.core import Settings

# Import our custom embedding model
try:
    from embedding_model import embed_model
except ImportError:
    embed_model = None


class StorageManager:
    """
    Manages persistence and storage for nodes and indexes in the regulatory tracker.
    Supports both file-based storage and vector store persistence.
    """
    
    def __init__(self, base_dir: str = "./storage"):
        self.base_dir = Path(base_dir)
        self.nodes_dir = self.base_dir / "nodes"
        self.indexes_dir = self.base_dir / "indexes"
        self.metadata_dir = self.base_dir / "metadata"
        self.chroma_dir = self.base_dir / "chroma_db"
        
        # Create directories if they don't exist
        self.nodes_dir.mkdir(parents=True, exist_ok=True)
        self.indexes_dir.mkdir(parents=True, exist_ok=True)
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
            use_chroma: Whether to use ChromaDB for persistence
            
        Returns:
            Path to the saved index
        """
        if use_chroma:
            # Use ChromaDB for persistent storage
            chroma_collection_name = f"{document_name}_collection"
            chroma_client = chromadb.PersistentClient(path=str(self.chroma_dir))
            
            # Create or get collection
            try:
                collection = chroma_client.get_collection(name=chroma_collection_name)
            except:
                collection = chroma_client.create_collection(name=chroma_collection_name)
            
            # Create vector store
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # Extract nodes from the original index
            nodes = list(index.docstore.docs.values())
            
            # Create a new index with the ChromaDB storage context
            # This will automatically save the embeddings to ChromaDB
            new_index = VectorStoreIndex(
                nodes,
                storage_context=storage_context
            )
            
            # Save metadata about the index
            metadata = {
                "document_name": document_name,
                "index_type": "vector",
                "storage_type": "chroma",
                "collection_name": chroma_collection_name,
                "node_count": len(nodes),
                "created_at": str(Path().stat().st_mtime)
            }
            
            metadata_file = self.metadata_dir / f"{document_name}_vector_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"Saved vector index to ChromaDB collection: {chroma_collection_name}")
            return str(self.indexes_dir / document_name)
        
        else:
            # Use simple file-based storage
            index_dir = self.indexes_dir / f"{document_name}_vector"
            index.storage_context.persist(persist_dir=str(index_dir))
            
            # Save metadata
            metadata = {
                "document_name": document_name,
                "index_type": "vector",
                "storage_type": "file",
                "node_count": len(index.docstore.docs),
                "created_at": str(Path().stat().st_mtime)
            }
            
            metadata_file = self.metadata_dir / f"{document_name}_vector_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"Saved vector index to {index_dir}")
            return str(index_dir)
    
    def load_vector_index(self, document_name: str, use_chroma: bool = True) -> Optional[VectorStoreIndex]:
        """
        Load vector index from storage.
        
        Args:
            document_name: Name identifier for the document
            use_chroma: Whether to use ChromaDB for loading
            
        Returns:
            VectorStoreIndex if found, None otherwise
        """
        if use_chroma:
            # Load from ChromaDB
            chroma_collection_name = f"{document_name}_collection"
            chroma_client = chromadb.PersistentClient(path=str(self.chroma_dir))
            
            try:
                collection = chroma_client.get_collection(name=chroma_collection_name)
                
                # Check if collection has any data
                if collection.count() == 0:
                    print(f"ChromaDB collection {chroma_collection_name} is empty")
                    return None
                
                vector_store = ChromaVectorStore(chroma_collection=collection)
                storage_context = StorageContext.from_defaults(vector_store=vector_store)
                
                # Set the embedding model globally before creating the index
                if embed_model:
                    Settings.embed_model = embed_model
                
                # Create the index from the vector store
                index = VectorStoreIndex.from_vector_store(
                    vector_store, 
                    storage_context=storage_context
                )
                
                print(f"Loaded vector index from ChromaDB collection: {chroma_collection_name}")
                return index
                
            except Exception as e:
                print(f"Error loading vector index from ChromaDB: {e}")
                return None
        
        else:
            # Load from file storage
            index_dir = self.indexes_dir / f"{document_name}_vector"
            
            if not index_dir.exists():
                print(f"No saved vector index found for {document_name}")
                return None
            
            try:
                storage_context = StorageContext.from_defaults(persist_dir=str(index_dir))
                
                # Set the embedding model if available
                if embed_model:
                    Settings.embed_model = embed_model
                
                index = VectorStoreIndex.from_vector_store(
                    storage_context.vector_store,
                    storage_context=storage_context
                )
                
                print(f"Loaded vector index from {index_dir}")
                return index
                
            except Exception as e:
                print(f"Error loading vector index: {e}")
                return None
    
    def save_summary_index(self, index: SummaryIndex, document_name: str) -> str:
        """
        Save summary index to disk.
        
        Args:
            index: SummaryIndex to save
            document_name: Name identifier for the document
            
        Returns:
            Path to the saved index
        """
        index_dir = self.indexes_dir / f"{document_name}_summary"
        index.storage_context.persist(persist_dir=str(index_dir))
        
        # Save metadata
        metadata = {
            "document_name": document_name,
            "index_type": "summary",
            "storage_type": "file",
            "node_count": len(index.docstore.docs),
            "created_at": str(Path().stat().st_mtime)
        }
        
        metadata_file = self.metadata_dir / f"{document_name}_summary_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Saved summary index to {index_dir}")
        return str(index_dir)
    
    def load_summary_index(self, document_name: str) -> Optional[SummaryIndex]:
        """
        Load summary index from disk.
        
        Args:
            document_name: Name identifier for the document
            
        Returns:
            SummaryIndex if found, None otherwise
        """
        index_dir = self.indexes_dir / f"{document_name}_summary"
        
        if not index_dir.exists():
            print(f"No saved summary index found for {document_name}")
            return None
        
        try:
            storage_context = StorageContext.from_defaults(persist_dir=str(index_dir))
            # Use the correct method for loading summary index from storage
            index = SummaryIndex.from_storage_context(storage_context)
            
            print(f"Loaded summary index from {index_dir}")
            return index
            
        except Exception as e:
            print(f"Error loading summary index: {e}")
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
        
        # Check for summary vector index metadata (for summary tool)
        summary_vector_metadata_file = self.metadata_dir / f"{document_name}_summary_vector_metadata.json"
        if summary_vector_metadata_file.exists():
            with open(summary_vector_metadata_file, 'r') as f:
                metadata['summary_vector_index'] = json.load(f)
        
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
            
            # Delete vector index
            vector_index_dir = self.indexes_dir / f"{document_name}_vector"
            if vector_index_dir.exists():
                import shutil
                shutil.rmtree(vector_index_dir)
            
            # Delete summary index
            summary_index_dir = self.indexes_dir / f"{document_name}_summary"
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
            
            # Delete ChromaDB collection if it exists
            try:
                chroma_client = chromadb.PersistentClient(path=str(self.chroma_dir))
                chroma_collection_name = f"{document_name}_collection"
                chroma_client.delete_collection(name=chroma_collection_name)
            except:
                pass  # Collection might not exist
            
            print(f"Successfully deleted all data for document: {document_name}")
            return True
            
        except Exception as e:
            print(f"Error deleting document {document_name}: {e}")
            return False 
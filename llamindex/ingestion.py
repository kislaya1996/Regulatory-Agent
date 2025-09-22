import os
from typing import List, Optional
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.ingestion import IngestionPipeline, IngestionCache
from llama_index.core.schema import BaseNode
from pdfplumber_reader import PDFPlumberReader
from storage_manager import StorageManager


def _is_valid_text(content: str, min_length: int = 50) -> bool:
    if not content or len(content) < min_length:
        return False
    if content.startswith('%PDF'):
        return False
    if ' 0 R ' in content[:100]:
        return False
    return True


def _validate_nodes(nodes: List[BaseNode]) -> List[BaseNode]:
    valid_nodes: List[BaseNode] = []
    for node in nodes:
        content = node.get_content()
        if _is_valid_text(content):
            valid_nodes.append(node)
    return valid_nodes


def extract_nodes_from_pdf(
    file_path: str,
    storage_manager: StorageManager,
    document_name: Optional[str] = None,
    chunk_size: int = 512,
    chunk_overlap: int = 25,
) -> List[BaseNode]:
    """
    Extract nodes from a PDF file. Uses cached/stored nodes when available.

    Args:
        file_path: Absolute path to the PDF
        storage_manager: StorageManager for persistence
        document_name: Optional explicit name; defaults to PDF basename sans extension
        chunk_size: Chunk size for sentence splitter
        chunk_overlap: Overlap for sentence splitter

    Returns:
        List of validated nodes
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if document_name is None:
        document_name = os.path.splitext(os.path.basename(file_path))[0]

    # Try load existing nodes
    existing_nodes = storage_manager.load_nodes(document_name)
    if existing_nodes:
        valid_nodes = _validate_nodes(existing_nodes)
        if valid_nodes:
            return valid_nodes

    # Fresh extraction
    pdf_reader = PDFPlumberReader()
    documents = pdf_reader.load_data(file_path)

    # Validate extracted documents
    valid_documents = []
    for doc in documents:
        content = doc.text or ""
        if _is_valid_text(content, min_length=100):
            valid_documents.append(doc)

    if not valid_documents:
        raise ValueError("No valid text content extracted from PDF")

    # Build ingestion pipeline with caching
    pipeline_with_cache = IngestionPipeline(
        transformations=[
            SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
        ],
        cache=IngestionCache(
            cache_dir="./cache",
            collection_name="regulatory_docs",
        ),
    )

    nodes = pipeline_with_cache.run(documents=valid_documents)

    # Final validation
    nodes = _validate_nodes(nodes)
    if not nodes:
        raise ValueError("No valid nodes after processing")

    # Persist
    storage_manager.save_nodes(nodes, document_name)
    return nodes 
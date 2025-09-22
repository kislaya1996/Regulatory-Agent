import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
load_dotenv()

from llama_index.core import Settings
from custom_llm import llm_indexing, llm_retrieval
from embedding_model import embed_model

from scraper import Scraper
from storage_manager import StorageManager
from ingestion import extract_nodes_from_pdf
from index_builders import build_tools_for_document


def iter_pdf_paths(download_paths: Iterable[str]) -> Iterable[str]:
    for p in download_paths:
        if p.lower().endswith('.pdf'):
            abs_p = os.path.abspath(p)
            if os.path.exists(abs_p):
                yield abs_p


def iter_local_pdfs(downloads_dir: str = "../downloads") -> Iterable[str]:
    """Iterate through all PDF files in the downloads directory recursively."""
    downloads_path = Path(downloads_dir)
    if not downloads_path.exists():
        print(f"Warning: Downloads directory {downloads_dir} does not exist")
        return
    
    for pdf_file in downloads_path.rglob("*.pdf"):
        yield str(pdf_file.absolute())


def process_pdf(file_path: str, storage: StorageManager, use_chroma: bool = True):
    document_name = os.path.splitext(os.path.basename(file_path))[0]

    # If already indexed (vector metadata exists), skip to next
    meta = storage.get_document_metadata(document_name)
    already_indexed = bool(meta.get('vector_index') or meta.get('summary_index'))
    if already_indexed:
        print(f"Skipping already indexed document: {document_name}")
        return

    print(f"Processing new document: {document_name}")

    # Set global models for ingestion
    Settings.llm = llm_indexing
    Settings.embed_model = embed_model

    # Extract nodes (loads existing nodes if present)
    nodes = extract_nodes_from_pdf(file_path=file_path, storage_manager=storage, document_name=document_name)

    # Switch to retrieval LLM for tool/query construction
    Settings.llm = llm_retrieval

    # Build or load indexes/tools
    build_tools_for_document(
        nodes=nodes,
        document_name=document_name,
        storage_manager=storage,
        use_chroma=use_chroma,
    )

    print(f"Finished indexing: {document_name}")


def run_scrape_and_index():
    """Run the full scraping and indexing pipeline."""
    # Configure base URL for scraping
    base_url = os.getenv("REGULATORY_SCRAPE_URL", "https://merc.gov.in/consumer-corner/tariff-orders")

    # Initialize storage under a dedicated directory
    storage = StorageManager(base_dir="./regulatory_storage")

    # Run scraper
    scraper = Scraper(base_url)
    print(f"Scraping listing: {base_url}")
    download_paths = scraper.scrape()

    # Iterate and process PDFs
    for pdf_path in iter_pdf_paths(download_paths):
        try:
            process_pdf(pdf_path, storage, use_chroma=True)
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")


def run_local_indexing(downloads_dir: str = "../downloads"):
    """Run indexing on already downloaded PDFs."""
    print(f"Processing local PDFs from: {downloads_dir}")
    
    # Initialize storage under a dedicated directory
    storage = StorageManager(base_dir="./regulatory_storage")

    # Count total PDFs for progress tracking
    pdf_files = list(iter_local_pdfs(downloads_dir))
    total_pdfs = len(pdf_files)
    
    if total_pdfs == 0:
        print(f"No PDF files found in {downloads_dir}")
        return
    
    print(f"Found {total_pdfs} PDF files to process")
    
    # Process each PDF
    for i, pdf_path in enumerate(pdf_files, 1):
        try:
            print(f"\n[{i}/{total_pdfs}] Processing: {os.path.basename(pdf_path)}")
            process_pdf(pdf_path, storage, use_chroma=True)
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
    
    print(f"\n✅ Completed processing {total_pdfs} PDF files")


if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--local":
        # Process local files
        downloads_dir = sys.argv[2] if len(sys.argv) > 2 else "../downloads"
        run_local_indexing(downloads_dir)
    else:
        # Default: scrape and index
        run_scrape_and_index() 
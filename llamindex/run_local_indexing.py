#!/usr/bin/env python3
"""
Local Indexing Script for Regulatory Tracker

This script processes already downloaded PDFs from the downloads folder
without requiring web scraping.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_scrape_index import run_local_indexing


def main():
    """Main function to run local indexing."""
    
    # Default downloads directory
    default_downloads_dir = "../downloads"
    
    # Check if downloads directory exists
    if not Path(default_downloads_dir).exists():
        print(f"❌ Downloads directory not found: {default_downloads_dir}")
        print("Please ensure you have PDF files in the downloads folder.")
        print("\nExpected structure:")
        print("regulatory-tracker/")
        print("├── downloads/")
        print("│   ├── orders/")
        print("│   │   └── document1.pdf")
        print("│   └── document2.pdf")
        print("└── llamindex/")
        return 1
    
    # Count PDF files
    pdf_count = len(list(Path(default_downloads_dir).rglob("*.pdf")))
    
    if pdf_count == 0:
        print(f"❌ No PDF files found in {default_downloads_dir}")
        print("Please add PDF files to the downloads directory first.")
        return 1
    
    print(f"🚀 Starting Local Indexing")
    print(f"📁 Source directory: {default_downloads_dir}")
    print(f"📄 Found {pdf_count} PDF files")
    print("=" * 50)
    
    try:
        # Run local indexing
        run_local_indexing(default_downloads_dir)
        print("\n✅ Local indexing completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Indexing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error during indexing: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 
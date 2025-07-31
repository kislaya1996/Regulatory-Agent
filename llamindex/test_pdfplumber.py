#!/usr/bin/env python3

import os
from pdfplumber_reader import PDFPlumberReader

def test_pdfplumber_extraction():
    """Test PDFPlumber text extraction on a sample page."""
    
    filename = "../downloads/orders/MSEDCL-MYT-Order_Case_no_217-of-2024.pdf"
    
    if not os.path.exists(filename):
        print(f"Error: File {filename} not found!")
        return
    
    print(f"Testing PDFPlumber extraction on: {filename}")
    
    # Create PDFPlumber reader
    pdf_reader = PDFPlumberReader()
    
    try:
        # Extract documents
        documents = pdf_reader.load_data(filename)
        
        print(f"\nExtracted {len(documents)} document sections")
        
        # Show sample content from first few documents
        for i, doc in enumerate(documents[:3]):
            print(f"\n--- Document {i+1} ---")
            print(f"Page: {doc.metadata.get('page_number', 'Unknown')}")
            print(f"Text length: {len(doc.text)} characters")
            print(f"Sample text (first 300 chars):")
            print(repr(doc.text[:300]))
            print("-" * 50)
        
        # Check for any corrupted content
        corrupted_count = 0
        for i, doc in enumerate(documents):
            if doc.text.startswith('%PDF') or ' 0 R ' in doc.text[:100]:
                corrupted_count += 1
                print(f"Corrupted content found in document {i+1}")
        
        if corrupted_count == 0:
            print(f"\n✓ All {len(documents)} documents have clean text content")
        else:
            print(f"\n✗ Found {corrupted_count} documents with corrupted content")
            
    except Exception as e:
        print(f"Error during extraction: {e}")

if __name__ == "__main__":
    test_pdfplumber_extraction() 
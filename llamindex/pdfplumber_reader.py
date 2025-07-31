import pdfplumber
from typing import List
from llama_index.core import Document
import os

class PDFPlumberReader:
    """
    Custom PDF reader using PDFPlumber for better text extraction from regulatory documents.
    """
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        """
        Initialize the PDFPlumber reader.
        
        Args:
            chunk_size: Size of text chunks to create
            overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def load_data(self, file_path: str) -> List[Document]:
        """
        Load and extract text from a PDF file using PDFPlumber.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of Document objects with extracted text
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        documents = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                print(f"Processing PDF with {len(pdf.pages)} pages...")
                
                for page_num, page in enumerate(pdf.pages):
                    # Extract text from the page
                    text = page.extract_text()
                    
                    if text and len(text.strip()) > 50:  # Only process pages with substantial text
                        # Clean the text
                        cleaned_text = self._clean_text(text)
                        
                        if cleaned_text:
                            # Create document with metadata
                            doc = Document(
                                text=cleaned_text,
                                metadata={
                                    "file_path": file_path,
                                    "file_name": os.path.basename(file_path),
                                    "page_number": page_num + 1,
                                    "total_pages": len(pdf.pages),
                                    "source_type": "pdf_plumber"
                                }
                            )
                            documents.append(doc)
                            print(f"Extracted {len(cleaned_text)} characters from page {page_num + 1}")
                        else:
                            print(f"Skipping page {page_num + 1} - no valid text content")
                    else:
                        print(f"Skipping page {page_num + 1} - insufficient text content")
        
        except Exception as e:
            print(f"Error processing PDF {file_path}: {e}")
            raise
        
        print(f"Successfully extracted text from {len(documents)} pages")
        return documents
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing unwanted characters and formatting.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove common PDF artifacts
        text = text.replace('\x00', '')  # Remove null bytes
        text = text.replace('\ufeff', '')  # Remove BOM
        
        # Remove lines that are likely PDF structure artifacts
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip lines that are likely PDF artifacts
            if (len(line) > 3 and 
                not line.startswith('%') and 
                not line.startswith('/') and
                not line.endswith(' 0 R') and
                not line.isdigit() and
                len(line.split()) > 1):  # At least 2 words
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at a sentence boundary
            if end < len(text):
                # Look for sentence endings
                for i in range(end, max(start + self.chunk_size - 100, start), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.overlap
            if start >= len(text):
                break
        
        return chunks 
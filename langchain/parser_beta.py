import os
from io import StringIO
import re
import unicodedata
from langdetect import detect, LangDetectException

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

class ParserBeta:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.document_content = []

        self.file_name = os.path.basename(pdf_path)
        self.file_name = os.path.splitext(self.file_name)[0]

        self.target_language = 'en'
        self.min_confidence_length = 30  # Minimum text length for reliable language detection
    
    def is_mostly_english(self, text):
        """
        Check if text is mostly English characters and not gibberish
        """
        if not text or len(text.strip()) < self.min_confidence_length:
            return True  # Too short to determine, keep it
            
        # Try to detect language
        try:
            detected_lang = detect(text)
            return detected_lang == self.target_language
        except LangDetectException:
            # If language detection fails, use character-based heuristics
            pass
            
        # Count Latin characters vs non-Latin
        latin_chars = sum(1 for c in text if c.isalpha() and unicodedata.name(c).startswith(('LATIN', 'DIGIT', 'SPACE')))
        total_chars = sum(1 for c in text if c.isalpha())
        
        if total_chars == 0:
            return True  # No alphabetic characters, keep it
            
        ratio = latin_chars / total_chars
        return ratio > 0.7  # If more than 70% are Latin characters, assume it's English
    
    def clean_text(self, text):
        """
        Clean text by removing gibberish and non-English content
        """
        # Break text into paragraphs
        paragraphs = text.split('\n\n')
        cleaned_paragraphs = []
        
        for para in paragraphs:
            # Skip empty paragraphs
            if not para.strip():
                continue
                
            # Clean paragraph of common OCR artifacts and strange characters
            cleaned_para = re.sub(r'[^\x00-\x7F]+', ' ', para)  # Remove non-ASCII characters
            cleaned_para = re.sub(r'\s+', ' ', cleaned_para)     # Normalize whitespace
            
            # Check if paragraph is mostly English
            if self.is_mostly_english(para):
                cleaned_paragraphs.append(cleaned_para)
        
        return '\n\n'.join(cleaned_paragraphs)
    
    def extract_text(self):

        with open(self.pdf_path, 'rb') as in_file:
            parser = PDFParser(in_file)
            doc = PDFDocument(parser)
            rsrcmgr = PDFResourceManager()
            
            for i, page in enumerate(PDFPage.create_pages(doc)):
                output_string = StringIO()

                # Use a custom LAParams to improve text extraction
                laparams = LAParams(
                    line_margin=0.5,
                    char_margin=2.0,
                    word_margin=0.1,
                    boxes_flow=0.5,
                    detect_vertical=True
                )

                device = TextConverter(rsrcmgr, output_string, laparams=laparams)
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                interpreter.process_page(page)
                
                raw_text = output_string.getvalue().strip()
                cleaned_text = self.clean_text(raw_text)

                if raw_text and len(raw_text.strip()) > 10:
                    self.document_content.append({
                        "page_number": i,
                        "content": cleaned_text,
                        "source": self.file_name
                    })

    def parse(self):
        self.extract_text()
        return self.document_content

    


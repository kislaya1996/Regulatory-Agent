import os
from io import StringIO

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

class Parser:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.document_content = []

        self.file_name = os.path.basename(pdf_path)
        self.file_name = os.path.splitext(self.file_name)[0]
    
    def extract_text(self):

        with open(self.pdf_path, 'rb') as in_file:
            parser = PDFParser(in_file)
            doc = PDFDocument(parser)
            rsrcmgr = PDFResourceManager()
            
            for i, page in enumerate(PDFPage.create_pages(doc)):
                output_string = StringIO()

                device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                interpreter.process_page(page)
                
                text = output_string.getvalue().strip()
                self.document_content.append({
                    "page_number": i,
                    "content": text,
                    "source": self.file_name
                })

    def parse(self):
        self.extract_text()
        return self.document_content

    


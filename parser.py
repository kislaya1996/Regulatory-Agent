import os
from unstructured.partition.pdf import partition_pdf
import fitz
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv()

class Parser:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.document_content = None
        self.elements = None

    def extract_elements(self):
        self.elements = partition_pdf(self.pdf_path, strategy="hi_res", chunking_strategy="by_title")

    
    def extract_text(self):
        text = ""
        with fitz.open(self.pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        
        self.document_content = text
    
    def get_table_desc(self, table_content, document_content):

        prompt = f"""
            Given the following table and its context from the original document,
            provide a detailed description of the table. Then, include the table in markdown format.

            Original Document Context:
            {document_content}

            Table Content:
            {table_content}

            Please provide:
            1. A comprehensive description of the table.
            2. The table in markdown format.
        """

        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        try:    
            response = client.messages.create(
                model="claude-3-7-sonnet-latest",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that describes tables and formats them in markdown."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0
            )

            return response.content.text
        
        except Exception as e:
            print(f"Error calling Anthropic API: {str(e)}")
            return None
        
    def process_each_table(self, document_content):
        for element in self.elements:
            if element.to_dict()['type'] == 'Table':
                table_content = element.to_dict()['text']
                result = self.get_table_desc(table_content, document_content)
                element.text = result

    def parse(self):
        self.extract_elements()
        self.extract_text()
        self.process_each_table(self.document_content)
        return self.elements, self.document_content

    


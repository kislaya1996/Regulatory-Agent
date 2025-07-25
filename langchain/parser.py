import os
import pdfplumber

class Parser:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.text_doc = []
        self.table_doc = []

        self.file_name = os.path.basename(pdf_path)
        self.file_name = os.path.splitext(self.file_name)[0]
    
    def extract_text(self):

        pdf = pdfplumber.open(self.pdf_path)

        last_table_heading = ""
        last_context = ""

        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            self.text_doc.append({"page_number": i+1, "content": text, "source": self.pdf_path})

            # Find table headings in the text (e.g., lines starting with "Table X:")
            lines = text.split('\n') if text else []
            table_headings = [line for line in lines if line.strip().startswith("Table")]

            tables = page.extract_tables()
            for table_idx, table in enumerate(tables):
                # Use the closest preceding table heading if available
                if table_idx < len(table_headings):
                    table_heading = table_headings[table_idx]
                    last_table_heading = table_heading
                    # Optionally, also update last_context here
                    start_idx = max(0, lines.index(table_heading) - 2)
                    end_idx = min(len(lines), lines.index(table_heading) + 3)
                    context_lines = lines[start_idx:end_idx]
                    context = "\n".join(context_lines)
                    last_context = context
                else:
                    table_heading = last_table_heading
                    context = last_context

                # Extract header and all rows as a single chunk
                table_header = [str(cell) for cell in table[0]]
                table_rows = ["|".join([str(cell) for cell in row]) for row in table[1:]]
                table_content = "|".join(table_header) + "\n" + "\n".join(table_rows)

                self.table_doc.append({
                    "page_number": i+1,
                    "content": f"{context}\n{table_content}",  # Include surrounding context
                    "source": self.pdf_path,
                    "table_heading": table_heading,
                    "header_row": "|".join(table_header),
                    "is_table": True  # Flag to identify table content
                })

    def parse(self):
        self.extract_text()
        return self.text_doc, self.table_doc

    


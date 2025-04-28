import pdfplumber
from db import DB
from indexer import Indexer
from chunker import Chunker

path = "downloads/orders/Final-MYT-Order-Case-No.-210-of-2024_TPC-D-280325.pdf"

pdf = pdfplumber.open(path)
text_doc = []
table_doc = []

last_table_heading = ""
last_context = ""

for i, page in enumerate(pdf.pages):
    text = page.extract_text()
    text_doc.append({"page_number": i+1, "content": text, "source": path})

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

        table_doc.append({
            "page_number": i+1,
            "content": f"{context}\n{table_content}",  # Include surrounding context
            "source": path,
            "table_heading": table_heading,
            "header_row": "|".join(table_header),
            "is_table": True  # Flag to identify table content
        })

chunker = Chunker(document=text_doc)
chunked_text = chunker.chunk()
print(f"Text Chunked!\n")

chunked_doc = chunked_text + table_doc

testing_db = DB(db_name="test_db", whoosh_index_dir="test_whoosh", embedding_model="BAAI/bge-large-en-v1.5")
collection = testing_db.get_collection()
whoosh_index = testing_db.get_whoosh_index()

indexer = Indexer(collection=collection, whoosh_index=whoosh_index, chunked_content=chunked_doc)
indexer.index()
indexer.index_whoosh()
print(f"Indexed!\n")

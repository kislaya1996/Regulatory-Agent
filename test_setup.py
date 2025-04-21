import pdfplumber
from db import DB
from indexer import Indexer
from chunker import Chunker

path = "downloads\\distribution\\3\\Final-Order-Case-No.-237-of-2023_TPC-D.pdf"

pdf = pdfplumber.open(path)
text_doc = []
table_doc = []

for i, page in enumerate(pdf.pages):
    text = page.extract_text()
    text_doc.append({"page_number": i+1, "content": text, "source": path})

    tables = page.extract_tables()
    
    for table in tables:
        table_data = []

        table_header = "|".join([str(cell) for cell in table[0]])
        table_header = table_header.replace("\n", " ")
        table_header += "\n"
        
        temp = table_header

        for row in table[1:]:
            row_text = "|".join([str(cell) for cell in row])
            row_text = row_text.replace("\n", " ")
            row_text += "\n"
            
            if len(temp) + len(row_text) > 512:
                table_data.append({"page_number": i+1, "content": temp, "source": path})
                temp = table_header
            
            temp += row_text

        table_doc.extend(table_data)


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

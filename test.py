from parser import Parser
from chunker import Chunker
from indexer import Indexer
from db import DB

db = DB(db_name="test")
collection = db.get_collection()

path = "downloads\\current-regulations-demand-side-management\\1\\DF-DSM-CC_-Notification-_17.01.2025.pdf"
parser = Parser(pdf_path=path)
parsed_content = parser.parse()

chunker = Chunker(document=parsed_content)
chunked_content = chunker.chunk()

indexer = Indexer(collection, chunked_content)
indexer.index()

result = db.query(["MERC"])
context = '\n\n'.join(result)

print(context)

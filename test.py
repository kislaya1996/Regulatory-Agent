from parser import Parser
from chunker import Chunker
from db import DB

db = DB(db_name="test")

path = "downloads\\current-regulations-demand-side-management\\1\\DF-DSM-CC_-Notification-_17.01.2025.pdf"
parser = Parser(pdf_path=path)
parsed_content = parser.parse()

chunker = Chunker(document=parsed_content)
chunked_content = chunker.chunk()

db.index(chunked_content)
result = db.query(["MERC"])
context = '\n\n'.join(result)

print(context)

from parser import Parser
from chunker import Chunker
from indexer import Indexer
from db import DB
from utilities import scrape_orders

print("Processing Orders")

order_url = "https://merc.gov.in/wp-admin/admin-ajax.php?action=getpostsfororderdatatables&_=1744051051853"
order_paths = scrape_orders(order_url)

mh_order_db = DB(db_name="maharashtra_orders")
mh_order_collection = mh_order_db.get_collection()

for path in order_paths:
    print(f"Processing {path}")

    parser = Parser(pdf_path=path)
    parsed_content = parser.parse()
    print(f"Parsed!\n")
    
    chunker = Chunker(document=parsed_content)
    chunked_content = chunker.chunk()
    print(f"Chunked!\n")

    indexer = Indexer(collection=mh_order_collection, chunked_content=chunked_content)
    indexer.index()
    print(f"Indexed!\n")

from parser import Parser
from chunker import Chunker
from indexer import Indexer
from db import DB
from utilities import scrape_orders

# order_url = "https://merc.gov.in/wp-admin/admin-ajax.php?action=getpostsfororderdatatables&_=1744051051853"
# order_paths = scrape_orders(order_url)

order_paths = {
    "karnataka_combined" : "downloads\orders\karnatak_combined_tariff_order.pdf", # Karnataka
    "adani" : "downloads\orders\AEML-D-Complete-Final-MYT-Order-28.03.2025-SD.pdf", # Adani
    "msedcl" : "downloads\orders\MSEDCL-MYT-Order_Case_no_217-of-2024.pdf", # MSEDCL
    "tata" : "downloads\orders\Final-MYT-Order-Case-No.-210-of-2024_TPC-D-280325.pdf" # Tata
}

for discom, path in order_paths.items():
    print(f"Processing {path}")

    parser = Parser(pdf_path=path)
    parsed_text, parsed_table = parser.parse()
    print("Parsed!\n")
    
    chunker = Chunker(document=parsed_text)
    chunked_text = chunker.chunk()
    chunked_content = chunked_text + parsed_table
    print("Chunked!\n")
    
    print(f"Creating DB for {discom}...\n")

    db = DB(db_name=f"{discom}_db", whoosh_index_dir=f"{discom}_whoosh", embedding_model="BAAI/bge-large-en-v1.5")
    collection = db.get_collection()
    whoosh_index = db.get_whoosh_index()

    indexer = Indexer(collection=collection, whoosh_index=whoosh_index, chunked_content=chunked_content)
    indexer.index()
    indexer.index_whoosh()
    print(f"Indexed!\n")

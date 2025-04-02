from scraper import Scraper
from parser import Parser
from chunker import Chunker
from indexer import Indexer
from db import DB
from llm import LLM

urls = [ 
    # Current Regulations
    "https://merc.gov.in/regulation_type/current-regulations-tariff-regulations/",
    "https://merc.gov.in/regulation_type/current-regulations-renewable-energy/",
    "https://merc.gov.in/regulation_type/current-regulations-open-access/",
    "https://merc.gov.in/regulation_type/current-regulations-demand-side-management/",
    "https://merc.gov.in/regulation_type/current-regulations-grid-operations/",

    # Existing Guidelines
    "https://merc.gov.in/guideline_type/existing-guidelines/",
    
    # Draft Regulations
    "https://merc.gov.in/regulation_type/draft-regulations/"
    ]

db = DB(db_name="maharashtra")
mh_collection = db.get_collection()

pdf_paths = set()

for url in urls:
    scraper = Scraper(base_url=url)
    save_paths = scraper.scrape()
    pdf_paths.update(save_paths)


for path in pdf_paths:
    print(f"Processing {path}")

    parser = Parser(pdf_path=path)
    parsed_document = parser.parse()

    print(f"Parsed!\n")
    
    chunker = Chunker(document=parsed_document)
    chunked_document = chunker.chunk()

    print(f"Chunked!\n")

    indexer = Indexer(collection=mh_collection, chunked_content=chunked_document, batch_size=5)
    indexed_document = indexer.index()

    print(f"Indexed!\n")

queries = [ "Maharashtra" ]
result = db.query(queries)
print(f'Query result{result}')

# llm = LLM()
# output = llm.ask(context="Rahul Gandhi is the Prime Minister of India", question="Who is the Prime Minister of India?")
# print(output)

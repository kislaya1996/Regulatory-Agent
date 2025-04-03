from scraper import Scraper
from parser import Parser
from chunker import Chunker
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

pdf_paths = set()

for url in urls:
    scraper = Scraper(base_url=url)
    save_paths = scraper.scrape()
    pdf_paths.update(save_paths)


for path in pdf_paths:
    print(f"Processing {path}")

    parser = Parser(pdf_path=path)
    parsed_content = parser.parse()
    print(f"Parsed!\n")
    
    chunker = Chunker(document=parsed_content)
    chunked_content = chunker.chunk()
    print(f"Chunked!\n")

    db.index(chunked_content)
    print(f"Indexed!\n")

queries = [ "subsidies" ]
result = db.query(queries)
context = '\n\n'.join(result)

llm = LLM()
output = llm.ask(context, question="What are the regional subsidies available in Maharashtra?")
print(output)

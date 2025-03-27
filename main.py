from scraper import Scraper
from parser import Parser
from chunker import Chunker
from indexer import Indexer

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

pdf_paths = set()

for url in urls:
    scraper = Scraper(base_url=url)
    save_paths = scraper.scrape()
    pdf_paths.update(save_paths)


for path in pdf_paths:
    parser = Parser(pdf_path=path)
    parsed_document = parser.parse()
    
    chunker = Chunker(document=parsed_document)
    chunked_document = chunker.chunk()

    indexer = Indexer(collection="Add Chroma DB Collection Here", chunked_content=chunked_document)


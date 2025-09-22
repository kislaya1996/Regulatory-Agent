# Regulatory Tracker

A comprehensive system for scraping, indexing, and querying regulatory documents using LlamaIndex and RAG.

## Overview

This system:
1. **Scrapes** regulatory documents from MERC website
2. **Downloads** PDFs to local storage
3. **Extracts** and **indexes** document content using LlamaIndex
4. **Provides** RAG-powered querying with vector search and summarization

## Prerequisites

### 1. Environment Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd regulatory-tracker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the root directory:
```bash
# AWS Credentials for Bedrock
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Optional: Custom scrape URL (defaults to MERC tariff orders)
REGULATORY_SCRAPE_URL=https://merc.gov.in/consumer-corner/tariff-orders
```

### 3. Directory Structure
Ensure these directories exist (they'll be created automatically):
```
regulatory-tracker/
├── downloads/          # Downloaded PDFs
├── regulatory_storage/ # Indexes and metadata
├── cache/             # Ingestion cache
└── embeddings_cache/  # Embedding model cache
```

## Step-by-Step Execution

### Option 1: Full Scraping and Indexing (Recommended for First Run)

#### Step 1: Scrape and Index Documents
```bash
# Navigate to the llamindex directory
cd llamindex

# Run the scraper and indexer
python run_scrape_index.py
```

**What this does:**
- Scrapes the MERC website for regulatory documents
- Downloads PDFs to `downloads/` directory
- Extracts text and creates nodes for each PDF
- Builds vector and summary indexes
- Stores everything in `regulatory_storage/`

**Expected output:**
```
Scraping listing: https://merc.gov.in/consumer-corner/tariff-orders
Downloaded: MSEDCL-MYT-Order_Case_no_217-of-2024.pdf
Processing new document: MSEDCL-MYT-Order_Case_no_217-of-2024
Creating new vector index for MSEDCL-MYT-Order_Case_no_217-of-2024
Creating new summary index for MSEDCL-MYT-Order_Case_no_217-of-2024
Finished indexing: MSEDCL-MYT-Order_Case_no_217-of-2024
```

### Option 2: Local Indexing (For Already Downloaded Files)

If you already have PDF files in the `downloads/` folder, you can skip scraping and just index them:

#### Method A: Using the Dedicated Script (Recommended)
```bash
cd llamindex
python run_local_indexing.py
```

#### Method B: Using Command Line Arguments
```bash
cd llamindex
python run_scrape_index.py --local
```

#### Method C: Custom Downloads Directory
```bash
cd llamindex
python run_scrape_index.py --local /path/to/your/pdfs
```

**What this does:**
- Scans the `downloads/` directory recursively for PDF files
- Skips already indexed documents
- Processes new PDFs and builds indexes
- Shows progress with file counts

**Expected output:**
```
🚀 Starting Local Indexing
📁 Source directory: ../downloads
📄 Found 5 PDF files
==================================================
[1/5] Processing: MSEDCL-MYT-Order_Case_no_217-of-2024.pdf
Processing new document: MSEDCL-MYT-Order_Case_no_217-of-2024
Creating new vector index for MSEDCL-MYT-Order_Case_no_217-of-2024
Creating new summary index for MSEDCL-MYT-Order_Case_no_217-of-2024
Finished indexing: MSEDCL-MYT-Order_Case_no_217-of-2024

[2/5] Processing: another-document.pdf
Skipping already indexed document: another-document

✅ Completed processing 5 PDF files
```

### Step 2: Test the RAG System
```bash
# Test with a specific document
python regulatory_tool_calling_test.py
```

**What this does:**
- Loads a specific regulatory document
- Creates vector search and summary tools
- Tests three types of queries:
  1. Specific content search
  2. Document summarization
  3. Structured data extraction

**Expected output:**
```
Loading/Processing Document: MSEDCL-MYT-Order_Case_no_217-of-2024.pdf
Loaded 45 nodes for MSEDCL-MYT-Order_Case_no_217-of-2024
Creating Tools for MSEDCL-MYT-Order_Case_no_217-of-2024
Testing Tools with Bedrock Claude Sonnet
Query 1: Asking about specific content...
Query 2: Asking for a summary...
Query 3: Asking about specific tariff details...
```

### Step 3: Interactive Querying (Optional)
You can also create your own query script:

```python
# custom_query.py
from llama_index.core import Settings
from custom_llm import llm_retrieval
from storage_manager import StorageManager
from ingestion import extract_nodes_from_pdf
from index_builders import build_tools_for_document

# Setup
Settings.llm = llm_retrieval
storage = StorageManager(base_dir="./regulatory_storage")

# Load document
document_name = "MSEDCL-MYT-Order_Case_no_217-of-2024"
nodes = storage.load_nodes(document_name)
vector_tool, summary_tool = build_tools_for_document(
    nodes=nodes, 
    document_name=document_name, 
    storage_manager=storage
)

# Query
response = llm_retrieval.predict_and_call(
    [vector_tool, summary_tool],
    "What are the tariff rates for industrial consumers?",
    verbose=True
)
print(response)
```

## Working with Local PDFs

### Adding Your Own PDFs
1. Place PDF files in the `downloads/` directory:
   ```
   downloads/
   ├── orders/
   │   ├── document1.pdf
   │   └── document2.pdf
   ├── reports/
   │   └── report1.pdf
   └── other-document.pdf
   ```

2. Run local indexing:
   ```bash
   cd llamindex
   python run_local_indexing.py
   ```

### Batch Processing
The system automatically:
- ✅ Skips already indexed documents
- ✅ Processes files recursively from subdirectories
- ✅ Shows progress with file counts
- ✅ Handles errors gracefully

### Custom Directory Structure
You can organize your PDFs however you want:
```
downloads/
├── 2024/
│   ├── Q1/
│   └── Q2/
├── 2023/
│   └── Annual/
└── Special/
```

The indexing will find all PDFs regardless of directory structure.

## System Architecture

### Core Modules

1. **`scraper.py`** - Web scraping for regulatory documents
2. **`ingestion.py`** - PDF text extraction and node creation
3. **`index_builders.py`** - Vector and summary index construction
4. **`storage_manager.py`** - Persistence and metadata management
5. **`run_scrape_index.py`** - Main orchestration script
6. **`run_local_indexing.py`** - Local PDF processing script

### Storage Structure

```
regulatory_storage/
├── nodes/                    # Extracted document nodes
├── vector_indexes/          # Vector search indexes
├── summary_indexes/         # Summary indexes
├── metadata/               # Index metadata
└── chroma_db/              # ChromaDB vector store
```

### LLM Configuration

- **Indexing**: Bedrock Nova Lite (faster, cheaper)
- **Retrieval**: Bedrock Claude 3.5 Sonnet (higher quality)
- **Embeddings**: BAAI/bge-small-en-v1.5

## Troubleshooting

### Common Issues

1. **PDF Download Fails**
   - Check internet connection
   - Verify the scrape URL is accessible
   - Check AWS credentials for Bedrock access

2. **Index Creation Fails**
   - Ensure sufficient disk space
   - Check AWS credentials and permissions
   - Verify PDF files are not corrupted

3. **Memory Issues**
   - Reduce chunk size in `ingestion.py`
   - Process documents one at a time
   - Increase system memory

4. **No PDFs Found**
   - Ensure PDF files are in the `downloads/` directory
   - Check file extensions are `.pdf` (lowercase)
   - Verify directory permissions

### Logs and Debugging

- Check console output for detailed error messages
- Look in `regulatory_storage/metadata/` for index status
- Verify ChromaDB collections in `regulatory_storage/chroma_db/`

## Performance Tips

1. **First Run**: May take 10-30 minutes depending on document size
2. **Subsequent Runs**: Much faster due to caching and existing indexes
3. **Large Documents**: Consider processing in batches
4. **Storage**: Ensure adequate disk space for indexes and embeddings
5. **Local Processing**: Faster than web scraping since no download time

## Customization

### Adding New Document Sources
1. Modify `scraper.py` to handle different websites
2. Update the base URL in `.env`
3. Adjust parsing logic for different document structures

### Changing LLM Models
1. Update `custom_llm.py` with new model configurations
2. Adjust temperature and other parameters as needed
3. Test with sample queries

### Modifying Index Settings
1. Adjust chunk size and overlap in `ingestion.py`
2. Modify similarity settings in tool factories
3. Change embedding model in `embedding_model.py`

## Next Steps

1. **Scale Up**: Process multiple document sources
2. **Add UI**: Create web interface for querying
3. **Enhance Queries**: Add more specialized query types
4. **Monitoring**: Add logging and performance metrics
5. **Deployment**: Containerize for production deployment 
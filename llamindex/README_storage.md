# Storage and Persistence for Regulatory Documents

This directory contains a comprehensive storage and persistence solution for the regulatory document processing system. The storage manager provides efficient ways to save, load, and manage processed nodes and indexes.

## Overview

The storage system consists of:

1. **StorageManager**: Main class for managing persistence
2. **Updated Tool Factories**: Modified to work with storage
3. **Updated Main Script**: Uses storage for efficiency
4. **Demo Script**: Shows how to use the storage functionality

## Features

### 🚀 **Persistent Storage**
- Save processed nodes to avoid reprocessing
- Store vector indexes with ChromaDB persistence
- Store summary indexes for quick access
- Metadata tracking for all stored components

### 🔄 **Smart Loading**
- Automatically check for existing data before processing
- Load indexes from storage when available
- Fallback to processing when no stored data exists

### 📊 **Storage Options**
- **ChromaDB**: Persistent vector storage with similarity search
- **File-based**: Simple file storage for indexes
- **Pickle**: Efficient node serialization

### 🛠 **Management Tools**
- List all stored documents
- Get metadata for any document
- Delete documents and their associated data
- Monitor storage usage

## Quick Start

### 1. Basic Usage

```python
from storage_manager import StorageManager

# Initialize storage manager
storage_manager = StorageManager(base_dir="./my_storage")

# Save processed nodes
storage_manager.save_nodes(nodes, "document_name")

# Load existing nodes (returns None if not found)
existing_nodes = storage_manager.load_nodes("document_name")

# Save vector index with ChromaDB
storage_manager.save_vector_index(vector_index, "document_name", use_chroma=True)

# Load vector index
loaded_index = storage_manager.load_vector_index("document_name", use_chroma=True)
```

### 2. Using with Tool Factories

```python
from vector_tool_factory import create_vector_query_tool
from summary_tool_factory import create_summary_tool

# Create tools with automatic persistence
vector_tool = create_vector_query_tool(
    nodes=nodes,
    document_name="my_document",
    storage_manager=storage_manager,
    use_chroma=True
)

summary_tool = create_summary_tool(
    nodes=nodes,
    document_name="my_document",
    storage_manager=storage_manager
)
```

### 3. Storage Management

```python
# List all stored documents
documents = storage_manager.list_documents()

# Get metadata for a document
metadata = storage_manager.get_document_metadata("document_name")

# Delete a document and all its data
storage_manager.delete_document("document_name")
```

## Directory Structure

```
storage/
├── nodes/                    # Processed nodes (pickle files)
│   ├── document1_nodes.pkl
│   └── document2_nodes.pkl
├── indexes/                  # Stored indexes
│   ├── document1_vector/     # Vector index files
│   ├── document1_summary/    # Summary index files
│   └── ...
├── metadata/                 # Metadata files
│   ├── document1_vector_metadata.json
│   ├── document1_summary_metadata.json
│   └── ...
└── chroma_db/               # ChromaDB database files
    └── ...
```

## Performance Benefits

### ⚡ **Speed Improvements**
- **First Run**: Process document and save everything
- **Subsequent Runs**: Load from storage (10-100x faster)
- **No Reprocessing**: Skip expensive LLM transformations

### 💾 **Storage Efficiency**
- **Nodes**: Compressed pickle storage
- **Indexes**: Optimized vector storage
- **Metadata**: JSON for easy inspection

### 🔍 **Search Performance**
- **ChromaDB**: Fast similarity search
- **Cached Embeddings**: No re-embedding needed
- **Indexed Content**: Quick retrieval

## Usage Examples

### Processing a New Document

```python
# Check if document already processed
existing_nodes = storage_manager.load_nodes(document_name)

if existing_nodes:
    print("Using existing processed nodes")
    nodes = existing_nodes
else:
    print("Processing new document")
    # Process document...
    nodes = process_document(filename)
    storage_manager.save_nodes(nodes, document_name)
```

### Creating Tools with Persistence

```python
# Vector tool will automatically save/load index
vector_tool = create_vector_query_tool(
    nodes=nodes,
    document_name=document_name,
    storage_manager=storage_manager,
    use_chroma=True
)

# Summary tool will automatically save/load index
summary_tool = create_summary_tool(
    nodes=nodes,
    document_name=document_name,
    storage_manager=storage_manager
)
```

### Managing Multiple Documents

```python
# List all processed documents
documents = storage_manager.list_documents()
print(f"Processed documents: {documents}")

# Get info about a specific document
metadata = storage_manager.get_document_metadata("MSEDCL-MYT-Order_Case_no_217-of-2024")
print(f"Document has {metadata['vector_index']['node_count']} nodes")

# Clean up old documents
storage_manager.delete_document("old_document")
```

## Configuration

### Storage Options

```python
# Use ChromaDB for vector storage (recommended)
storage_manager.save_vector_index(index, "doc", use_chroma=True)

# Use file-based storage (simpler)
storage_manager.save_vector_index(index, "doc", use_chroma=False)
```

### Custom Storage Directory

```python
# Store in custom location
storage_manager = StorageManager(base_dir="/path/to/storage")

# Store in project subdirectory
storage_manager = StorageManager(base_dir="./regulatory_storage")
```

## Error Handling

The storage manager includes robust error handling:

- **Missing Files**: Gracefully handles missing stored data
- **Corrupted Data**: Attempts to recover or fallback to processing
- **Storage Errors**: Provides clear error messages
- **Permissions**: Handles file permission issues

## Best Practices

### 📁 **Organization**
- Use descriptive document names
- Keep storage directory organized
- Regular cleanup of old documents

### 🔒 **Security**
- Don't commit storage directory to version control
- Use appropriate file permissions
- Backup important processed data

### ⚡ **Performance**
- Use ChromaDB for production systems
- Monitor storage usage
- Clean up unused documents

## Troubleshooting

### Common Issues

1. **"No saved nodes found"**
   - Document hasn't been processed yet
   - Check if document name matches

2. **"Error loading vector index"**
   - ChromaDB collection might be corrupted
   - Try deleting and recreating the index

3. **"Permission denied"**
   - Check file permissions on storage directory
   - Ensure write access

### Debug Mode

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check storage status
metadata = storage_manager.get_document_metadata("document_name")
print(json.dumps(metadata, indent=2))
```

## Migration from Old System

If you're migrating from the old system without storage:

1. **First Run**: Process all documents (will be slower)
2. **Automatic Storage**: New system will save everything
3. **Future Runs**: Will be much faster with stored data

## API Reference

### StorageManager Methods

- `save_nodes(nodes, document_name)` - Save processed nodes
- `load_nodes(document_name)` - Load existing nodes
- `save_vector_index(index, document_name, use_chroma=True)` - Save vector index
- `load_vector_index(document_name, use_chroma=True)` - Load vector index
- `save_summary_index(index, document_name)` - Save summary index
- `load_summary_index(document_name)` - Load summary index
- `get_document_metadata(document_name)` - Get document metadata
- `list_documents()` - List all stored documents
- `delete_document(document_name)` - Delete document and all data

### Tool Factory Updates

- `create_vector_query_tool()` now accepts `storage_manager` parameter
- `create_summary_tool()` now accepts `storage_manager` parameter
- Both automatically handle save/load operations

## Demo

Run the demo script to see the storage system in action:

```bash
python storage_demo.py
```

This will demonstrate:
- Document processing and storage
- Index creation and persistence
- Loading from storage
- Metadata management
- Storage operations 
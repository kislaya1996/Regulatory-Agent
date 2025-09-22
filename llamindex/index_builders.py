from typing import List, Tuple
from llama_index.core.schema import BaseNode
from storage_manager import StorageManager
from vector_tool_factory import create_vector_query_tool
from summary_tool_factory import create_summary_tool


def build_tools_for_document(
    nodes: List[BaseNode],
    document_name: str,
    storage_manager: StorageManager,
    use_chroma: bool = True,
):
    """
    Build (or load) and return vector and summary tools for a document.
    """
    vector_tool = create_vector_query_tool(
        nodes=nodes,
        document_name=document_name,
        storage_manager=storage_manager,
        use_chroma=use_chroma,
    )

    summary_tool = create_summary_tool(
        nodes=nodes,
        document_name=document_name,
        storage_manager=storage_manager,
        use_chroma=use_chroma,
    )

    return vector_tool, summary_tool 
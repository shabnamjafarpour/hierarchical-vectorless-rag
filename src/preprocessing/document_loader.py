from langchain_community.document_loaders import PyPDFLoader


# """
# اين فايل مياد pdf خام رو تبديل ميكنه به يك representation قابل استفاده در اينجا
# """
# It loads the PDF into page-level LangChain Documents.
# I preserve page boundaries and combine selected page 
# ranges into temporary text windows for downstream structure discovery and semantic extraction.

def load_document(file_path: str):
    """Load a PDF and return its pages as LangChain Documents."""
    loader = PyPDFLoader(file_path)
    # هر داكيومنت langchain دو چيز دارد
    # document.page_content
    # document.metadata
    return loader.load()

# No. These are page-based processing windows.
# The actual retrieval units are semantic nodes 
# extracted later in the preprocessing pipeline

def combine_pages(
    
    documents,
    start: int,
    end: int
) -> str:

    """Combine a range of document pages into a single string."""
    return "\n\n".join(
        f"PAGE {index + 1}\n{documents[index].page_content}"
        for index in range(start, end)
    )
    

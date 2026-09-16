from langchain_community.document_loaders import PyPDFLoader


def load_document(file_path: str):
    loader = PyPDFLoader(file_path)
    return loader.load()


def combine_pages(
    documents,
    start: int,
    end: int
) -> str:

    return "\n\n".join(
        f"PAGE {index + 1}\n{documents[index].page_content}"
        for index in range(start, end)
    )
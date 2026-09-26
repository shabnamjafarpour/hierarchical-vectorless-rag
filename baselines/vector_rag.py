from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-base"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 5


def load_embedding_model() -> HuggingFaceEmbeddings:
    """
    Load the multilingual embedding model used by the
    standard vector-based RAG baseline.
    """
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME
    )


def load_document(file_path: str) -> List[Document]:
    """
    Load a PDF document page by page.
    """
    loader = PyPDFLoader(file_path)
    return loader.load()


def chunk_documents(
    documents: List[Document],
) -> List[Document]:
    """
    Split PDF pages into fixed-size overlapping chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    return splitter.split_documents(documents)


def build_vector_store(
    chunks: List[Document],
    embedding_model: HuggingFaceEmbeddings,
) -> FAISS:
    """
    Embed document chunks and build a FAISS vector index.
    """
    print(
        f"[BASELINE] Building FAISS index "
        f"from {len(chunks)} chunks..."
    )

    vector_store = FAISS.from_documents(
        chunks,
        embedding_model,
    )

    print("[BASELINE] FAISS index created.")

    return vector_store


def save_vector_store(
    vector_store: FAISS,
    index_path: str,
) -> None:
    """
    Persist the FAISS index locally.
    """
    vector_store.save_local(index_path)

    print(
        f"[BASELINE] FAISS index saved to: {index_path}"
    )


def load_vector_store(
    index_path: str,
    embedding_model: HuggingFaceEmbeddings,
) -> FAISS:
    """
    Load an existing FAISS index from disk.
    """
    print(
        f"[BASELINE] Loading existing FAISS index "
        f"from: {index_path}"
    )

    return FAISS.load_local(
        index_path,
        embedding_model,
        allow_dangerous_deserialization=True,
    )


def get_or_create_vector_store(
    pdf_path: str,
    index_path: str,
    embedding_model: HuggingFaceEmbeddings,
) -> FAISS:
    """
    Load a cached FAISS index when available.
    Otherwise, build and persist a new index.
    """
    index_directory = Path(index_path)

    if index_directory.exists():
        return load_vector_store(
            index_path=index_path,
            embedding_model=embedding_model,
        )

    print("[BASELINE] No cached FAISS index found.")

    documents = load_document(pdf_path)

    print(
        f"[BASELINE] Loaded {len(documents)} PDF pages."
    )

    chunks = chunk_documents(documents)

    print(
        f"[BASELINE] Created {len(chunks)} chunks."
    )

    vector_store = build_vector_store(
        chunks=chunks,
        embedding_model=embedding_model,
    )

    save_vector_store(
        vector_store=vector_store,
        index_path=index_path,
    )

    return vector_store


def retrieve(
    query: str,
    vector_store: FAISS,
    top_k: int = TOP_K,
) -> List[Document]:
    """
    Retrieve the top-k most similar chunks for a query.
    """
    return vector_store.similarity_search(
        query,
        k=top_k,
    )
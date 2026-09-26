import json
import re
import time
from pathlib import Path

from src.config import load_model
from baselines.vector_rag import (
    get_or_create_vector_store,
    load_embedding_model,
    retrieve,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "evaluation_dataset.json"
)

RESULTS_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "baseline_evaluation_results.json"
)

PDF_PATH = r"D:\AI_REPOSITORY_CACHE_MI\projects\AradBook\docs\external_data.pdf"

INDEX_PATH = str(
    PROJECT_ROOT
    / "storage"
    / "baseline_faiss"
)

TOP_K = 5


def load_evaluation_dataset() -> list[dict]:
    """Load the shared evaluation dataset."""
    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def extract_identifiers_from_chunk(text: str) -> list[str]:
    """
    Extract all ARAD identifiers contained in a retrieved chunk.
    """
    return re.findall(
        r"ARAD-\d{4}",
        text,
        flags=re.IGNORECASE,
    )


def calculate_retrieval_hit(
    retrieved_identifiers: list[str],
    expected_identifiers: list[str],
) -> bool | None:
    """
    Check whether all expected identifiers occur in the
    retrieved top-k chunks.

    Document-level questions have no identifier-based
    retrieval ground truth.
    """
    if not expected_identifiers:
        return None

    retrieved_set = {
        identifier.upper()
        for identifier in retrieved_identifiers
    }

    return all(
        expected_id.upper() in retrieved_set
        for expected_id in expected_identifiers
    )


def generate_answer(
    query: str,
    retrieved_documents,
    llm,
) -> str:
    """
    Generate a grounded answer using only retrieved chunks.
    """
    context = "\n\n".join(
        document.page_content
        for document in retrieved_documents
    )

    prompt = f"""
You are a question-answering assistant.

Answer the user's question using only the provided context.

Do not use outside knowledge.

If the requested information is not available in the context,
clearly state that the information does not exist in the document.

Context:
{context}

Question:
{query}

Answer:
"""

    response = llm.invoke(prompt)

    return response.content


def save_results(results: list[dict]) -> None:
    """Persist evaluation progress after every query."""
    with open(
        RESULTS_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )


def evaluate():
    print("\n================================")
    print(" VECTOR RAG BASELINE EVALUATION")
    print("================================\n")

    dataset = load_evaluation_dataset()

    embedding_model = load_embedding_model()

    vector_store = get_or_create_vector_store(
        pdf_path=PDF_PATH,
        index_path=INDEX_PATH,
        embedding_model=embedding_model,
    )

    llm = load_model()

    results = []

    for index, item in enumerate(dataset, start=1):

        question = item["question"]

        print(
            f"\n[{index}/{len(dataset)}] "
            f"{item['id']} - {item['category']}"
        )
        print(f"Question: {question}")

        # -------------------------------
        # Retrieval
        # -------------------------------

        retrieval_start = time.perf_counter()

        retrieved_documents = retrieve(
            query=question,
            vector_store=vector_store,
            top_k=TOP_K,
        )

        retrieval_latency = (
            time.perf_counter()
            - retrieval_start
        )

        retrieved_identifiers = []

        for document in retrieved_documents:
            retrieved_identifiers.extend(
                extract_identifiers_from_chunk(
                    document.page_content
                )
            )

        # Remove duplicates while preserving order.
        retrieved_identifiers = list(
            dict.fromkeys(retrieved_identifiers)
        )

        retrieval_hit = calculate_retrieval_hit(
            retrieved_identifiers,
            item["expected_identifiers"],
        )

        # -------------------------------
        # Generation
        # -------------------------------

        generation_start = time.perf_counter()

        answer = generate_answer(
            query=question,
            retrieved_documents=retrieved_documents,
            llm=llm,
        )

        generation_latency = (
            time.perf_counter()
            - generation_start
        )

        end_to_end_latency = (
            retrieval_latency
            + generation_latency
        )

        # -------------------------------
        # Result
        # -------------------------------

        result = {
            "id": item["id"],
            "category": item["category"],
            "question": question,
            "expected_answer": item["expected_answer"],
            "actual_answer": answer,
            "answerable": item["answerable"],
            "expected_identifiers": (
                item["expected_identifiers"]
            ),
            "retrieved_identifiers": (
                retrieved_identifiers
            ),
            "retrieval_hit": retrieval_hit,
            "retrieval_latency_ms": round(
                retrieval_latency * 1000,
                2,
            ),
            "generation_latency_ms": round(
                generation_latency * 1000,
                2,
            ),
            "end_to_end_latency_ms": round(
                end_to_end_latency * 1000,
                2,
            ),
        }

        results.append(result)

        save_results(results)

        print(
            f"Retrieved identifiers: "
            f"{retrieved_identifiers}"
        )
        print(
            f"Retrieval Hit: {retrieval_hit}"
        )
        print(
            f"Answer: {answer}"
        )
        print(
            "Retrieval latency: "
            f"{result['retrieval_latency_ms']} ms"
        )
        print(
            "End-to-end latency: "
            f"{result['end_to_end_latency_ms']} ms"
        )

    print("\n================================")
    print(" BASELINE EVALUATION FINISHED")
    print("================================")

    print(
        f"\nResults saved to:\n{RESULTS_PATH}"
    )


if __name__ == "__main__":
    evaluate()
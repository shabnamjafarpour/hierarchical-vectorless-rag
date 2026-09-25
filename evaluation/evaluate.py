import json
import time
from pathlib import Path

from src.config import load_model
from src.document_manager import load_processed_document
from src.retrieval.tree_retriever import retrieve_from_tree
from src.generation.answer_generator import generate_answer
import arabic_reshaper
from bidi.algorithm import get_display

# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "evaluation_dataset.json"
)

RESULTS_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "evaluation_results.json"
)

DOCUMENT_ID = (
    "5b09dc878b013d79cdf29c9fcdf9dc26"
    "ac608d5a4e3796179f80b3af11896aab"
)


# --------------------------------------------------
# Helper functions
# --------------------------------------------------
def fa(text: str) -> str:
    """
    Format Persian text for terminal display only.
    """
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)


def load_evaluation_dataset() -> list[dict]:
    """Load the benchmark questions and ground-truth annotations."""
    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def extract_identifier(node: dict) -> str:
    """
    Extract the stable ARAD identifier from node metadata.
    """
    metadata = node.get("metadata", {})

    identifier = metadata.get("identifier", "")

    return str(identifier).strip()


def calculate_retrieval_hit(
    retrieved_nodes: list[dict],
    expected_identifiers: list[str],
) -> bool | None:
    """
    Check whether all expected nodes were retrieved.

    Returns None for document-level questions that do not
    have an expected semantic-node identifier.
    """
    if not expected_identifiers:
        return None

    retrieved_identifiers = {
        extract_identifier(node)
        for node in retrieved_nodes
        if extract_identifier(node)
    }

    return all(
        expected_id in retrieved_identifiers
        for expected_id in expected_identifiers
    )


def save_results(results: list[dict]) -> None:
    """Persist evaluation progress so completed queries survive later provider failures."""
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


# --------------------------------------------------
# Evaluation
# --------------------------------------------------

def evaluate():
    """Run retrieval and grounded generation across the evaluation dataset."""
    print("\n================================")
    print(" RAG EVALUATION")
    print("================================\n")

    dataset = load_evaluation_dataset()

    processed_document = load_processed_document(
        DOCUMENT_ID
    )

    tree = processed_document["tree"]

    llm = load_model()

    results = []

    for index, item in enumerate(dataset, start=1):

        question = item["question"]

        print(
            f"\n[{index}/{len(dataset)}] "
            f"{item['id']} - {item['category']}"
        )
        print(f"Question: {fa(question)}")

        # -------------------------------
        # Retrieval evaluation
        # -------------------------------

        retrieval_start = time.perf_counter()

        retrieved_nodes = retrieve_from_tree(
            tree=tree,
            query=question,
            llm=llm,
            top_k=5,
        )

        retrieval_latency = (
            time.perf_counter()
            - retrieval_start
        )

        retrieved_identifiers = [
            extract_identifier(node)
            for node in retrieved_nodes
            if extract_identifier(node)
        ]

        retrieval_hit = calculate_retrieval_hit(
            retrieved_nodes,
            item["expected_identifiers"],
        )

        # -------------------------------
        # Answer generation
        # -------------------------------

        generation_start = time.perf_counter()

        answer = generate_answer(
            query=question,
            retrieved_nodes=retrieved_nodes,
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
        # Store result
        # -------------------------------

        result = {
            "id": item["id"],
            "category": item["category"],
            "question": question,

            "expected_answer": (
                item["expected_answer"]
            ),

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

        # Save after every question.
        # Persist after each query so provider failures do not discard earlier results.
        save_results(results)

        print(
            f"Retrieved: {fa(retrieved_identifiers)}"
        )

        print(
            f"Retrieval Hit: {fa(retrieval_hit)}"
        )

        print(
            f"Answer: {fa(answer)}"
        )

        print(
            "Retrieval latency: "
            f"{fa(result['retrieval_latency_ms'])} ms"
        )

        print(
            "End-to-end latency: "
            f"{fa(result['end_to_end_latency_ms'])} ms"
        )

    print("\n================================")
    print(" EVALUATION FINISHED")
    print("================================")

    print(
        f"\nResults saved to:\n{RESULTS_PATH}"
    )


if __name__ == "__main__":
    evaluate()

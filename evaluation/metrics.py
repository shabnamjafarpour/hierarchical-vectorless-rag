import json
import statistics
from pathlib import Path


RESULTS_PATH = Path(__file__).parent / "evaluation_results.json"


# Manual evaluation of generated answers.
#
# q12 is intentionally excluded from the primary benchmark because
# the current question has multiple valid answers while its ground
# truth contains only one identifier.
ANSWER_CORRECTNESS = {
    "q01": True,
    "q02": True,
    "q03": True,
    "q04": True,
    "q05": True,
    "q06": True,
    "q07": True,
    "q08": True,
    "q09": True,
    "q10": False,
    "q11": True,
    "q13": True,
    "q14": True,
    "q15": True,
    "q16": True,
    "q17": True,
    "q18": True,
    "q19": True,
    "q20": True,
}


EXCLUDED_FROM_PRIMARY_BENCHMARK = {
    "q12": "Ambiguous ground truth: multiple answers satisfy the query."
}


def load_results() -> list[dict]:
    with open(RESULTS_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def calculate_retrieval_metrics(results: list[dict]) -> dict:
    """
    Calculate Hit@5 only for questions with retrieval ground truth.

    Document-level questions have retrieval_hit=None and are therefore
    not part of this metric.

    Ambiguous benchmark items are excluded from the primary score.
    """

    evaluated = [
        result
        for result in results
        if result.get("retrieval_hit") is not None
        and result["id"] not in EXCLUDED_FROM_PRIMARY_BENCHMARK
    ]

    hits = sum(
        1
        for result in evaluated
        if result["retrieval_hit"] is True
    )

    total = len(evaluated)

    return {
        "hits": hits,
        "total": total,
        "hit_at_5": hits / total if total else 0.0,
    }


def calculate_answer_correctness() -> dict:
    correct = sum(ANSWER_CORRECTNESS.values())
    total = len(ANSWER_CORRECTNESS)

    return {
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else 0.0,
    }


def calculate_unanswerable_accuracy(results: list[dict]) -> dict:
    """
    Uses manually reviewed answer correctness for questions marked
    answerable=False.
    """

    unanswerable = [
        result
        for result in results
        if result.get("answerable") is False
    ]

    correct = sum(
        1
        for result in unanswerable
        if ANSWER_CORRECTNESS.get(result["id"]) is True
    )

    total = len(unanswerable)

    return {
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else 0.0,
    }


def calculate_latency_metrics(results: list[dict]) -> dict:
    retrieval = [
        result["retrieval_latency_ms"]
        for result in results
    ]

    generation = [
        result["generation_latency_ms"]
        for result in results
    ]

    end_to_end = [
        result["end_to_end_latency_ms"]
        for result in results
    ]

    return {
        "retrieval_mean_ms": mean(retrieval),
        "retrieval_median_ms": median(retrieval),

        "generation_mean_ms": mean(generation),
        "generation_median_ms": median(generation),

        "end_to_end_mean_ms": mean(end_to_end),
        "end_to_end_median_ms": median(end_to_end),
    }


def print_metrics(
    retrieval: dict,
    answers: dict,
    unanswerable: dict,
    latency: dict,
):
    print("\n================================")
    print("       EVALUATION METRICS")
    print("================================")

    print("\nRetrieval")
    print("--------------------------------")
    print(
        f"Hit@5:                  "
        f"{retrieval['hit_at_5'] * 100:.2f}% "
        f"({retrieval['hits']}/{retrieval['total']})"
    )

    print("\nGeneration")
    print("--------------------------------")
    print(
        f"Answer Correctness:     "
        f"{answers['accuracy'] * 100:.2f}% "
        f"({answers['correct']}/{answers['total']})"
    )

    print(
        f"Unanswerable Accuracy:  "
        f"{unanswerable['accuracy'] * 100:.2f}% "
        f"({unanswerable['correct']}/{unanswerable['total']})"
    )

    print("\nLatency")
    print("--------------------------------")
    print(
        f"Retrieval Mean:         "
        f"{latency['retrieval_mean_ms']:.2f} ms"
    )
    print(
        f"Retrieval Median:       "
        f"{latency['retrieval_median_ms']:.2f} ms"
    )

    print(
        f"Generation Mean:        "
        f"{latency['generation_mean_ms'] / 1000:.2f} s"
    )
    print(
        f"Generation Median:      "
        f"{latency['generation_median_ms'] / 1000:.2f} s"
    )

    print(
        f"End-to-End Mean:        "
        f"{latency['end_to_end_mean_ms'] / 1000:.2f} s"
    )
    print(
        f"End-to-End Median:      "
        f"{latency['end_to_end_median_ms'] / 1000:.2f} s"
    )

    print("\nBenchmark Notes")
    print("--------------------------------")

    for question_id, reason in EXCLUDED_FROM_PRIMARY_BENCHMARK.items():
        print(f"{question_id}: excluded - {reason}")

    print("\n================================")


def main():
    results = load_results()

    retrieval = calculate_retrieval_metrics(results)
    answers = calculate_answer_correctness()
    unanswerable = calculate_unanswerable_accuracy(results)
    latency = calculate_latency_metrics(results)

    print_metrics(
        retrieval,
        answers,
        unanswerable,
        latency,
    )


if __name__ == "__main__":
    main()
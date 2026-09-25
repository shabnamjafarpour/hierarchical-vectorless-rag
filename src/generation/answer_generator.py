from src.utils.llm_utils import response_to_text

from src.retrieval.tree_retriever import (
    retrieve_from_tree,
    is_complete_list_query,
)


# =========================================================
# Context construction
# =========================================================

def build_context(
    retrieved_nodes: list[dict],
) -> str:
    """
    Convert retrieved semantic nodes into a compact
    context for answer generation.
    """

    context_parts = []

    for index, node in enumerate(
        retrieved_nodes,
        start=1,
    ):

        path = " > ".join(
            node.get(
                "path",
                [],
            )
        )

        metadata = node.get(
            "metadata",
            {},
        )

        context_parts.append(
            f"""
SOURCE {index}

Title:
{node.get("title", "")}

Type:
{node.get("type", "")}

Path:
{path}

Content:
{node.get("content", "")}

Metadata:
{metadata}
""".strip()
        )

    return "\n\n---\n\n".join(
        context_parts
    )


# =========================================================
# Deterministic complete-list generation
# =========================================================

def generate_complete_list_answer(
    retrieved_nodes: list[dict],
) -> str:
    """
    Generate a complete list directly from retrieved nodes.

    No LLM call is required.

    This prevents the generation model from accidentally
    omitting items from large list-style answers.
    """

    if not retrieved_nodes:
        return (
            "اطلاعاتی برای نمایش "
            "در داکیومنت پیدا نشد."
        )

    items = []

    for node in retrieved_nodes:

        title = str(
            node.get(
                "title",
                "",
            )
        ).strip()

        if not title:
            continue

        metadata = node.get(
            "metadata",
            {},
        )

        author = str(
            metadata.get(
                "author",
                "",
            )
            or ""
        ).strip()

        status = str(
            metadata.get(
                "status",
                "",
            )
            or ""
        ).strip()

        details = []

        if author:
            details.append(
                f"نویسنده: {author}"
            )

        if status:
            details.append(
                f"وضعیت: {status}"
            )

        if details:
            item = (
                f"**{title}** "
                f"({', '.join(details)})"
            )
        else:
            item = f"**{title}**"

        items.append(item)

    if not items:
        return (
            "اطلاعاتی برای نمایش "
            "در داکیومنت پیدا نشد."
        )

    formatted_items = "\n".join(
        f"{index}. {item}"
        for index, item
        in enumerate(
            items,
            start=1,
        )
    )

    return (
        f"لیست کامل موارد موجود در "
        f"داکیومنت ({len(items)} مورد):\n\n"
        f"{formatted_items}"
    )


# =========================================================
# LLM answer generation
# =========================================================

def generate_answer(
    query: str,
    retrieved_nodes: list[dict],
    llm,
) -> str:
    """
    Generate a grounded answer using retrieved context.
    """

    if not retrieved_nodes:
        return (
            "اطلاعات مرتبطی در داکیومنت "
            "برای پاسخ به این سؤال پیدا نکردم."
        )

    context = build_context(
        retrieved_nodes
    )

    prompt = f"""
You are a document question-answering assistant.

Answer the user's question using ONLY the provided
document context.

User question:

{query}

Document context:

{context}

Instructions:

1. Use only information supported by the document context.

2. Do not use external knowledge.

3. Do not invent facts.

4. Answer in the same language as the user's question.

5. Interpret the user's language naturally.
   The user may use informal Persian, spelling variations,
   spacing variations, or colloquial suffixes.

   Examples:
   - "کتاب هارو بگو" means "کتاب‌ها را بگو".
   - "هارو" is NOT the name of an entity or book.
   - "کتابا" may mean "کتاب‌ها".
   - Persian and Arabic character variants should be
     interpreted naturally.

6. If the user asks about a specific item, answer only
   with information relevant to that item.

7. If several retrieved items are relevant to the
   question, include all relevant items.

8. If the user applies a filter such as topic, author,
   availability, category, or another property, respect
   that filter using the provided context.

9. Distinguish between:
   - an item being part of the document
   - an item's availability/status.

   Do not assume that an item with status such as
   "امانت داده شده" is absent from the document.

10. For recommendation-style questions, make the
    recommendation only from the retrieved document
    information and briefly explain the document-based
    reason.

11. Internal system labels such as:
    "Document",
    "root",
    "semantic node",
    or hierarchy labels
    are NOT necessarily the real document title.

    Never present an internal system label as the real
    document title unless the context explicitly states
    that it is the title.

12. If the user asks for the document name/title and
    the actual title is not explicitly present in the
    context, say that the exact title is not available
    in the processed information.

13. If the context genuinely does not contain enough
    information to answer the question, clearly say so.

14. Be concise and direct unless the user explicitly
    asks for a detailed answer.

Return only the final answer.
"""

    print(
        f">>> Generating answer for: {query}"
    )

    try:

        response = llm.invoke(
            prompt
        )

        answer = response_to_text(
            response
        ).strip()

        if not answer:
            return (
                "مدل پاسخی تولید نکرد."
            )

        return answer

    except Exception as error:

        print(
            f">>> Answer generation failed: "
            f"{error}"
        )

        return (
            "در زمان تولید پاسخ خطایی رخ داد. "
            "لطفاً دوباره تلاش کنید."
        )


# =========================================================
# Main QA entry point
# =========================================================

def answer_question(
    query: str,
    document_tree: dict,
    llm,
) -> dict:
    """
    Main document QA function.

    Complete-list queries:
        local retrieval
        -> deterministic Python answer
        -> zero generation LLM calls

    Other queries:
        local retrieval
        -> LLM generation
        -> one generation LLM call
    """

    query = str(
        query or ""
    ).strip()

    if not query:
        return {
            "answer": "لطفاً یک سؤال وارد کنید.",
            "retrieved_nodes": [],
        }

    # -----------------------------------------------------
    # Retrieval
    # -----------------------------------------------------

    retrieved_nodes = retrieve_from_tree(
        tree=document_tree,
        query=query,
        llm=llm,
    )

    print(
        f">>> Retrieved "
        f"{len(retrieved_nodes)} nodes."
    )

    # -----------------------------------------------------
    # Complete-list query
    # -----------------------------------------------------

    if is_complete_list_query(query):

        print(
            ">>> Answer mode: "
            "DETERMINISTIC_COMPLETE_LIST"
        )

        answer = generate_complete_list_answer(
            retrieved_nodes
        )

        return {
            "answer": answer,
            "retrieved_nodes": retrieved_nodes,
        }

    # -----------------------------------------------------
    # Normal grounded generation
    # -----------------------------------------------------

    print(
        ">>> Answer mode: LLM_GENERATION"
    )

    answer = generate_answer(
        query=query,
        retrieved_nodes=retrieved_nodes,
        llm=llm,
    )

    return {
        "answer": answer,
        "retrieved_nodes": retrieved_nodes,
    }

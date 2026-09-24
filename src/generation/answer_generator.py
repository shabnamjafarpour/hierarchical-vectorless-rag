from src.utils.llm_utils import response_to_text
from src.retrieval.tree_retriever import (
    retrieve_from_tree,
)

def build_context(
    retrieved_nodes: list[dict],
) -> str:
    """
    Convert retrieved semantic nodes into
    context for answer generation.
    """

    context_parts = []

    for index, node in enumerate(
        retrieved_nodes,
        start=1,
    ):
        path = " > ".join(
            node.get("path", [])
        )

        context_parts.append(
            f"""
SOURCE {index}

Title: {node.get("title", "")}

Type: {node.get("type", "")}

Path: {path}

Content:
{node.get("content", "")}

Metadata:
{node.get("metadata", {})}
""".strip()
        )

    return "\n\n---\n\n".join(
        context_parts
    )
    
    
    
def generate_answer(
    query: str,
    retrieved_nodes: list[dict],
    llm,
) -> str:
    """
    Generate a grounded answer using only
    the retrieved document context.
    """

    if not retrieved_nodes:
        return (
            "I could not find relevant information "
            "in the document to answer this question."
        )

    context = build_context(
        retrieved_nodes
    )

    prompt = f"""
You are a document question-answering assistant.

Answer the user's question using ONLY the
information provided in the document context.

User question:

{query}

Document context:

{context}

Instructions:

- Use only information supported by the context.
- Do not invent facts.
- Do not use external knowledge.
- If the context does not contain enough information
  to answer the question, clearly say so.
- Answer in the same language as the user's question.
- Give a clear and direct answer.
- When multiple relevant items exist, include all
  relevant items supported by the context.

Return only the final answer.
"""

    print(
        f">>> Generating answer for: {query}"
    )

    response = llm.invoke(prompt)

    return response_to_text(
        response
    ).strip()
    
    
def answer_question(
    query: str,
    document_tree: dict,
    llm,
) -> dict:
    """
    Run retrieval and answer generation for
    a user question.
    """

    retrieved_results = retrieve_from_tree(
        tree=document_tree,
        query=query,
        llm=llm,
    )
    retrieved_nodes = retrieved_results['retrieved_nodes']
    retrieved_traced = retrieved_results['retrieval_trace']
    print(
        f">>> Retrieved "
        f"{len(retrieved_nodes)} nodes."
    )

    answer = generate_answer(
        query=query,
        retrieved_nodes=retrieved_nodes,
        llm=llm,
    )

    return {
        "answer": answer,
        "retrieved_nodes": retrieved_nodes,
        "retrieved_traced" :retrieved_traced
    }    
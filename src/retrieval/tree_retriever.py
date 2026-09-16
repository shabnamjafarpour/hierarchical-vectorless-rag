import json

from src.utils.json_utils import parse_llm_json

def _build_children_index(node: dict) -> list[dict]:
    """
    Create a compact representation of the direct
    children of a tree node for retrieval.
    """

    children_index = []

    for index, child in enumerate(
        node.get("children", [])
    ):
        children_index.append(
            {
                "index": index,
                "title": child.get("title", ""),
                "type": child.get("type", ""),
                "summary": child.get("summary", ""),
            }
        )

    return children_index


def select_relevant_children(
    node: dict,
    query: str,
    llm,
) -> list[dict]:
    """
    Select one or more direct children that may
    contain information relevant to the query.
    """

    children = node.get("children", [])

    if not children:
        return []

    children_index = _build_children_index(node)

    children_text = json.dumps(
        children_index,
        indent=2,
        ensure_ascii=False,
    )

    prompt = f"""
You are navigating a hierarchical document tree
to retrieve information relevant to a user's query.

Current node:

Title: {node.get("title", "")}
Type: {node.get("type", "")}

User query:

{query}

Direct children of the current node:

{children_text}

Determine which children may contain information
useful for answering the query.

IMPORTANT:

Multiple children may be relevant.

Select ALL children that are reasonably relevant.

Do not force a selection when none of the children
are relevant.

Return ONLY valid JSON:

{{
    "selected_indexes": [0, 2]
}}

Rules:

- selected_indexes must contain only indexes
  present in the provided children.
- Multiple indexes are allowed.
- Do not select unrelated children.
- If none are relevant, return:
  {{"selected_indexes": []}}
- Return ONLY JSON.
- Do not use Markdown.
"""

    response = llm.invoke(prompt)

    try:
        result = parse_llm_json(response)

    except (json.JSONDecodeError, TypeError, ValueError):

        print(
            f">>> Retrieval JSON parsing failed "
            f"at node: {node.get('title', '')}"
        )

        return []

    selected_indexes = result.get(
        "selected_indexes",
        [],
    )

    selected_children = []

    for index in selected_indexes:

        if (
            isinstance(index, int)
            and 0 <= index < len(children)
        ):
            selected_children.append(
                children[index]
            )

    return selected_children




def retrieve_from_tree(
    tree: dict,
    query: str,
    llm,
    max_depth: int = 10,
) -> list[dict]:
    """
    Traverse a hierarchical document tree and
    retrieve relevant semantic nodes.
    """

    retrieved_nodes = []

    def traverse(
        node: dict,
        depth: int,
        path: list[str],
    ) -> None:

        if depth > max_depth:
            return

        current_path = path + [
            node.get("title", "")
        ]

        children = node.get(
            "children",
            [],
        )

        content = node.get(
            "content",
            "",
        )

        # ----------------------------------
        # Leaf / semantic node
        # ----------------------------------

        if content:

            retrieved_nodes.append(
                {
                    "title": node.get(
                        "title",
                        "",
                    ),
                    "type": node.get(
                        "type",
                        "",
                    ),
                    "content": content,
                    "metadata": node.get(
                        "metadata",
                        {},
                    ),
                    "entities": node.get(
                        "entities",
                        [],
                    ),
                    "summary": node.get(
                        "summary",
                        "",
                    ),
                    "path": current_path,
                }
            )

            return

        # ----------------------------------
        # No content and no children
        # ----------------------------------

        if not children:
            return

        # ----------------------------------
        # Select relevant branches
        # ----------------------------------

        selected_children = (
            select_relevant_children(
                node=node,
                query=query,
                llm=llm,
            )
        )

        # ----------------------------------
        # Traverse selected branches
        # ----------------------------------

        for child in selected_children:

            traverse(
                node=child,
                depth=depth + 1,
                path=current_path,
            )

    traverse(
        node=tree,
        depth=0,
        path=[],
    )

    return retrieved_nodes
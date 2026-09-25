from src.utils.llm_utils import response_to_text


def build_document_tree(
    semantic_nodes: list[dict],
    document_structure: dict,
) -> dict:

    """Arrange semantic nodes into the hierarchy inferred during structure discovery."""
    tree = {
        "title": "Document",
        "type": "root",
        "document_type": document_structure.get(
            "document_type",
            "unknown",
        ),


        "semantic_unit": document_structure.get(
            "semantic_unit",
            "",
        ),


        "summary": "",
        "children": [],
    }


    hierarchy = document_structure.get(
        "hierarchy",
        [],
    )

    # -----------------------------------------
    # Case 1: No hierarchy detected
    # -----------------------------------------

    if not hierarchy:

        for node in semantic_nodes:


            tree["children"].append(
                {
                    "title": node.get("title", ""),
                    "type": node.get(
                        "node_type",
                        "unknown",
                    ),
                    "content": node.get(
                        "content",
                        "",
                    ),
                    "metadata": node.get(
                        "metadata",
                        {},
                    ),
                    "entities": node.get(
                        "entities",
                        [],
                    ),
                    "summary": "",
                    "children": [],


                }
            )

        return tree

    # -----------------------------------------
    # Case 2: Hierarchy exists
    # -----------------------------------------


   # -----------------------------------------
    # If hierarchy exists


    #     Document
    # │
    # ├── Science
    # │   ├── Article A
    # │   └── Article B
    # │
    # └── History
    #     ├── Article C
    #     └── Article D


    # -----------------------------------------


    for node in semantic_nodes:

        current_level = tree

        metadata = node.get(
            "metadata",
            {},
        )


# hierarchy = [
#     "category",
#     "subcategory"
# ]


        for hierarchy_level in hierarchy:


            level_name = str(
                hierarchy_level
            )


# metadata = {
#     "category": "Science"
# }


            level_value = metadata.get(
                level_name
            )


            # This semantic node does not contain
            # this hierarchy level.


            if not level_value:
                continue

            existing_child = None


            # Check whether this hierarchy node
            # already exists.


            for child in current_level["children"]:


# metadata = {
#     "category": "Science"
# }

# level_name = "category"
# level_value = "Science"


# Document
# ├── Science
# ├── Science
# ├── Science
# ├── Science
# ...

# Document
# └── Science
#     ├── Article 1
#     ├── Article 2
#     ├── Article 3
#     └── ...


                if (
                    child.get("type") == level_name
                    and
                    child.get("title")
                    == str(level_value)
                ):
                    existing_child = child
                    break

            # Create hierarchy node if necessary.
            if existing_child is None:


                existing_child = {
                    "title": str(level_value),
                    "type": level_name,
                    "summary": "",
                    "children": [],
                }


                current_level["children"].append(
                    existing_child
                )

            # Move one level deeper in the tree.
            current_level = existing_child


# current_level
#       ↓
#    Document

# Document
#     │
#     └── Science
#             ↑
#       current_level


# -----------------------------------------
# Add actual semantic node
# -----------------------------------------


        semantic_node = {
            "title": node.get(
                "title",
                "",
            ),
            "type": node.get(
                "node_type",
                "unknown",
            ),
            "content": node.get(
                "content",
                "",
            ),
            "metadata": metadata,
            "entities": node.get(
                "entities",
                [],
            ),
            "summary": "",
            "children": [],
        }

        current_level["children"].append(
            semantic_node
        )

    return tree


def _collect_child_context(node: dict) -> str:
    """
    Build compact context from a node's direct children
    for generating a retrieval-oriented parent summary.
    """

    child_contexts = []

    for child in node.get("children", []):

        title = child.get("title", "")
        summary = child.get("summary", "")
        content = child.get("content", "")

        child_text = summary or content

        if child_text:
            child_contexts.append(
                f"Title: {title}\n"
                f"Information: {child_text}"
            )

    return "\n\n".join(child_contexts)


def add_node_summaries(
    node: dict,
    llm,
) -> dict:

    # -----------------------------------------
    # 1. Process children first
    # -----------------------------------------

    """Generate bottom-up summaries so internal tree nodes retain retrieval context."""
    for child in node.get("children", []):
        add_node_summaries(
            child,
            llm,
        )

    # -----------------------------------------
    # 2. Determine summary source
    # -----------------------------------------

    content = node.get(
        "content",
        "",
    ).strip()

    if content:
        summary_source = content

    else:
        summary_source = _collect_child_context(
            node
        )

    # Nothing useful to summarize
    if not summary_source:
        return node

    # -----------------------------------------
    # 3. Generate retrieval-oriented summary
    # -----------------------------------------

    prompt = f"""
You are generating a retrieval-oriented summary
for a node in a hierarchical document tree.

The summary will be used later to decide whether
this node is relevant to a user's query.

Node title:

{node.get("title", "")}

Node type:

{node.get("type", "")}

Node information:

{summary_source}

Create a concise retrieval-oriented summary.

Focus on:

- what information this node contains
- important topics
- important entities
- key concepts
- information useful for deciding whether
  this node is relevant to a query

Rules:

- Do not invent information.
- Preserve the original language.
- Do not add external knowledge.
- Be concise.
- Return ONLY the summary.
"""

    print(
        f">>> Generating summary: "
        f"{node.get('title', 'Untitled')}"
    )

    response = llm.invoke(prompt)

    node["summary"] = (
        response_to_text(response).strip()
    )

    return node

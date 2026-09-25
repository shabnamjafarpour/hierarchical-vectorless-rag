import json

from src.preprocessing.document_loader import combine_pages
from src.utils.json_utils import parse_llm_json

# SEMANTIC UNIT EXTRACTION


# - node_type
# - title
# - content

# - entities


# No overlap
#     ↓
# risk of losing boundary context

# Overlap
#     ↓
# better context preservation
#     ↓
# but possible duplicates
#     ↓
# Consolidation

def extract_semantic_units(
    documents,
    document_structure: dict,
    llm,
    window_size: int = 3,
    overlap: int = 1,
) -> list[dict]:

    """Extract structured semantic retrieval units from overlapping page windows."""
    all_nodes = []

    step = window_size - overlap

    for start in range(0, len(documents), step):

        end = min(
            start + window_size,
            len(documents),
        )

        print(
            f"Semantic extraction: "
            f"pages {start + 1}---{end}"
        )

        document_text = combine_pages(
            documents,
            start,
            end,
        )

        structure_text = json.dumps(
            document_structure,
            indent=2,
            ensure_ascii=False,
        )

        prompt = f"""
You are a semantic document extraction system.

The global document schema has already been discovered.

Document type:

{document_structure.get("document_type", "")}

Semantic unit type:

{document_structure.get("semantic_unit", "")}

Document schema:

{structure_text}

Now extract the semantic units contained
in the following pages.

IMPORTANT:

PDF page boundaries are NOT semantic boundaries.

A semantic unit may start on one page
and continue on another page.

Preserve the complete semantic unit whenever
possible.

For every semantic unit return:

- node_type
- title
- content
- metadata
- entities

Return ONLY valid JSON:

{{
    "nodes": [
        {{
            "node_type": "",
            "title": "",
            "content": "",
            "metadata": {{}},
            "entities": []
        }}
    ]
}}

Rules:

- Do not invent information.
- Preserve original content.
- Do not summarize content.
- Separate different semantic units.
- Preserve semantic units that continue across pages.
- metadata should contain structured information
  explicitly present in the document.
- entities should contain important named entities.
- Return ONLY JSON.
- Do not use Markdown.

Document pages:

{document_text}
"""

        print(
            f">>> Sending semantic extraction request "
            f"for pages {start + 1}-{end}"
        )

        response = llm.invoke(prompt)

        print(
            f">>> Semantic extraction response received "
            f"for pages {start + 1}-{end}"
        )

        try:
            extracted_data = parse_llm_json(response)

            nodes = extracted_data.get(
                "nodes",
                [],
            )

            all_nodes.extend(nodes)

            print(
                f">>> Extracted {len(nodes)} nodes"
            )

        except json.JSONDecodeError as error:
            print(
                f"Could not parse semantic nodes "
                f"for pages {start + 1}-{end}"
            )
            print("JSON ERROR:", error)
            print("RAW LLM RESPONSE:")
            print(response.content)

        if end == len(documents):
            break

    return all_nodes


#consolidate semantic nodes --------------------------------


def consolidate_semantic_nodes(
    nodes: list[dict],
    llm,
    batch_size: int = 10,
) -> list[dict]:

    """Merge duplicate or overlapping semantic units produced by batched extraction."""
    consolidated_nodes = []

    for start in range(
        0,
        len(nodes),
        batch_size,
    ):
        batch = nodes[
            start:start + batch_size
        ]

        nodes_text = json.dumps(
            batch,
            indent=2,
            ensure_ascii=False,
        )

        prompt = f"""
You are a semantic node consolidation system.

The following semantic nodes were extracted
from overlapping windows of the same document.

Some nodes may represent the same semantic unit.

Your task is to:

1. Identify duplicate or overlapping nodes.
2. Merge nodes that belong to the same semantic unit.
3. Preserve the complete original content.
4. Keep distinct semantic units separate.

Input nodes:

{nodes_text}

Return ONLY valid JSON:

{{
    "nodes": [
        {{
            "node_type": "",
            "title": "",
            "content": "",
            "metadata": {{}},
            "entities": []
        }}
    ]
}}

Rules:

- Do not invent information.
- Do not summarize content.
- Do not remove meaningful information.
- Merge only nodes that clearly represent
  the same semantic unit.
- Preserve the original language.
- Return ONLY JSON.
- Do not use Markdown.
"""

        print(
            f">>> Consolidating nodes "
            f"{start + 1}-{start + len(batch)}"
        )

        response = llm.invoke(prompt)

        try:
            result = parse_llm_json(response)

            batch_nodes = result.get(
                "nodes",
                [],
            )

            consolidated_nodes.extend(
                batch_nodes
            )

            print(
                f">>> Consolidated batch returned "
                f"{len(batch_nodes)} nodes"
            )

        except json.JSONDecodeError as error:
            print(
                "Could not consolidate node batch."
            )
            print("Error:", error)
            print("Response:", response.content)

    return consolidated_nodes


# Fixed-size chunking is simpler and cheaper. In this project,
# I intentionally moved more computation to offline preprocessing to
# construct semantically meaningful retrieval units and preserve document hierarchy.
# Since processed documents are cached, that preprocessing cost is paid
# once per unique document, while query-time retrieval operates on the persisted tree.


# Expensive preprocessing
#         ↓
# done once
#         ↓
# SHA-256 document_id
#         ↓
# persistent storage
#         ↓
# next upload → load cached tree

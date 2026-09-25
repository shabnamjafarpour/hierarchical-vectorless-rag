import json

from src.preprocessing.document_loader import combine_pages
from src.utils.json_utils import parse_llm_json


# 1. document_type
# 2. semantic_unit
# 3. fields
# 4. hierarchy


def discover_document_structure_batch(
    documents,
    llm,
    batch_size: int = 5,
) -> list[dict]:

    """Infer partial document schemas from page batches to cover the full document."""
    partial_structures = []


# 1. document_type
# 2. semantic_unit
# 3. fields
# 4. hierarchy
    for start in range(
        0,
        len(documents),
        batch_size,
    ):
        end = min(
            start + batch_size,
            len(documents),
        )


        print(
            f"Discovering structure between "
            f"pages {start + 1}---{end}"
        )


        document_text = combine_pages(
            documents,
            start,
            end,
        )


        prompt = f"""
You are a document structure discovery system.

Analyze the following document pages and identify
the HIGH-LEVEL semantic structure of the document.

Do NOT extract individual records yet.

Determine:

1. document_type
2. semantic_unit
3. fields
4. hierarchy

Hierarchy must contain ONLY field names
that describe relationships between records.

Example:

[
    "category",
    "author"
]

Do NOT put document titles or section names.

The semantic unit means the type of meaningful
record/entity contained in the document.

Examples include:

- product
- book
- person
- article
- event
- organization
- case
- topic
- record

Return ONLY valid JSON.

The JSON must be complete.
Do not stop before closing all brackets.

If content is large, return fewer nodes instead
of incomplete JSON.

{{
    "document_type": "",
    "semantic_unit": "",
    "fields": [],
    "hierarchy": []
}}

Rules:

- Do not extract actual records.
- Do not list individual items.
- Do not summarize the document.
- Do not invent information.
- Preserve the original language.
- Return ONLY JSON.
- Do not use Markdown.

Document pages:

{document_text}
"""

        print(">>> SENDING REQUEST TO LANGUAGE MODEL...")
        print(f">>> INPUT LENGTH: {len(document_text)} characters")
        response = llm.invoke(prompt)

        print(">>> LANGUAGE MODEL RESPONSE RECEIVED")
        print(">>> RESPONSE TYPE:", type(response.content))

        try:
            structure = parse_llm_json(response)
            partial_structures.append(structure)

        except json.JSONDecodeError as error:
            print(
                f"Could not parse structure for "
                f"pages {start + 1}-{end}."
            )
            print("Error:", error)
            print("Response:", response.content)

    return partial_structures


# Build Global Structure From Document


        # {{
        #     "document_type": "",
        #     "semantic_unit": "",
        #     "fields": [],
        #     "hierarchy": []
        # }}


def merge_document_structures(
    partial_structures: list[dict],
    llm,
) -> dict:


    """Consolidate batch-level schemas into one global document structure."""
    structures_text = json.dumps(
        partial_structures,
        indent=2,
        ensure_ascii=False,
    )

    prompt = f"""
You are a document schema consolidation system.

Several partial document structure analyses
were extracted from different parts of the same document.

Your task is to merge them into ONE global schema.

Partial structures:

{structures_text}

Return ONLY valid JSON using exactly:

{{
    "document_type": "",
    "semantic_unit": "",
    "fields": [],
    "hierarchy": []
}}

Rules:

- Merge duplicate fields.
- Preserve all meaningful fields.
- Resolve minor naming differences.
- Do not invent fields.
- Do not extract actual records.
- Do not summarize the document.
- Return ONLY JSON.
- Do not use Markdown.
"""

    response = llm.invoke(prompt)

    try:
        return parse_llm_json(response)


    except json.JSONDecodeError as error:
        print("Could not merge document structures.")
        print("Error:", error)
        print("Response:", response.content)

        return {
            "document_type": "unknown",
            "semantic_unit": "",
            "fields": [],
            "hierarchy": [],
        }

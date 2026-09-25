from pathlib import Path

from src.document_manager import (
    calculate_document_id,
    document_exists,
    load_processed_document,
    save_processed_document,
)

from src.preprocessing.document_loader import (
    load_document,
)

from src.preprocessing.structure_extractor import (
    discover_document_structure_batch,
    merge_document_structures,
)

from src.preprocessing.semantic_extractor import (
    extract_semantic_units,
    consolidate_semantic_nodes,
)

from src.preprocessing.tree_builder import (
    build_document_tree,
    add_node_summaries,
)


# process_document(...)


def process_document(
    file_path: str,
    llm,
    model_name: str,
    pipeline_version: str = "1.0",
) -> dict:
    """
    Load a previously processed document from storage,
    or run the complete preprocessing pipeline for a
    new document and persist the results.
    """

    # -----------------------------------------
    # 1. Calculate document ID
    # -----------------------------------------

    document_id = calculate_document_id(
        file_path
    )

    print(
        f"\n>>> Document ID: {document_id}"
    )

    # -----------------------------------------
    # 2. Check persistent cache
    # -----------------------------------------

    if document_exists(document_id):

        print(
            ">>> Document already processed."
        )

        print(
            ">>> Loading from persistent storage..."
        )

        return load_processed_document(
            document_id
        )

    print(
        ">>> New document detected."
    )

    print(
        ">>> Starting preprocessing pipeline..."
    )

    # -----------------------------------------
    # 3. Load PDF
    # -----------------------------------------

    documents = load_document(
        file_path
    )

    print(
        f">>> Loaded {len(documents)} pages."
    )

    # -----------------------------------------
    # 4. Structure Discovery
    # -----------------------------------------

    print(
        "\n>>> STEP 1: Structure Discovery"
    )

    partial_structures = (
        discover_document_structure_batch(
            documents=documents,
            llm=llm,
            batch_size=5,
        )
    )

    document_structure = (
        merge_document_structures(
            partial_structures=partial_structures,
            llm=llm,
        )
    )

    # -----------------------------------------
    # 5. Semantic Extraction
    # -----------------------------------------

    print(
        "\n>>> STEP 2: Semantic Extraction"
    )

    semantic_nodes = extract_semantic_units(
        documents=documents,
        document_structure=document_structure,
        llm=llm,
        window_size=3,
        overlap=1,
    )

    # -----------------------------------------
    # 6. Consolidation
    # -----------------------------------------

    print(
        "\n>>> STEP 3: Node Consolidation"
    )

    consolidated_nodes = (
        consolidate_semantic_nodes(
            nodes=semantic_nodes,
            llm=llm,
            batch_size=5,
        )
    )

    print(
        f">>> Nodes before consolidation: "
        f"{len(semantic_nodes)}"
    )

    print(
        f">>> Nodes after consolidation: "
        f"{len(consolidated_nodes)}"
    )

    # -----------------------------------------
    # 7. Tree Construction
    # -----------------------------------------

    print(
        "\n>>> STEP 4: Tree Construction"
    )

    document_tree = build_document_tree(
        semantic_nodes=consolidated_nodes,
        document_structure=document_structure,
    )

    # -----------------------------------------
    # 8. Retrieval Summaries
    # -----------------------------------------

    print(
        "\n>>> STEP 5: Generating Node Summaries"
    )

    document_tree = add_node_summaries(
        node=document_tree,
        llm=llm,
    )

    # -----------------------------------------
    # 9. Persist processed document
    # -----------------------------------------

    print(
        "\n>>> STEP 6: Saving processed document"
    )

    save_processed_document(
        document_id=document_id,
        filename=Path(file_path).name,
        num_pages=len(documents),
        document_structure=document_structure,
        semantic_nodes=consolidated_nodes,
        document_tree=document_tree,
        model_name=model_name,
        pipeline_version=pipeline_version,
    )

    print(
        ">>> Document successfully saved."
    )

    # -----------------------------------------
    # 10. Return same format as cache load
    # -----------------------------------------

    return load_processed_document(
        document_id
    )

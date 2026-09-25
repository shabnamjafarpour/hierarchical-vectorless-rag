import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


STORAGE_DIR = Path("storage/documents")
# PDF
#  ↓
# Document ID
#  ↓

#  ├── YES → Load cached result
#  └── NO  → Preprocess → Save result


#================================================

# 7a8f86c5f36b61c4c8a96e4f...

#================================================

def calculate_document_id(file_path: str) -> str:
    """
    Calculate a SHA-256 hash for a document.

    The hash is used as the unique document ID.
    """


    sha256 = hashlib.sha256()


    with open(file_path, "rb") as file:
        while chunk := file.read(8192):
            sha256.update(chunk)


    return sha256.hexdigest()


# ABC123/
# │
# ├── metadata.json
# ├── structure.json
# ├── semantic_nodes.json
# └── tree.json


def get_document_directory(
    document_id: str,
) -> Path:
    """
    Return the storage directory for a document.
    """

    return STORAGE_DIR / document_id


def document_exists(
    document_id: str,
) -> bool:
    """
    Check whether a document has already been
    fully preprocessed.
    """

    document_dir = get_document_directory(
        document_id
    )


    required_files = [
        "metadata.json",
        "structure.json",
        "semantic_nodes.json",
        "tree.json",
    ]


# all([True, True, True, True])
# True


    return all(
        (document_dir / filename).exists()
        for filename in required_files
    )


def save_json(
    data,
    file_path: Path,
) -> None:
    """
    Save Python data as UTF-8 JSON.
    """

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        file_path,
        "w",
        encoding="utf-8",
    ) as file:
    #json.dump()
    #Python → JSON File
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )

def load_json(
    file_path: Path,
):
    """
    Load JSON data from disk.
    """

    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_processed_document(
    document_id: str,
    filename: str,
    num_pages: int,
    document_structure: dict,
    semantic_nodes: list[dict],
    document_tree: dict,
    model_name: str,
    pipeline_version: str = "1.0",
) -> None:

    """Persist preprocessing artifacts and metadata under the content-addressed document directory."""
    document_dir = get_document_directory(
        document_id
    )

    document_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata = {
        "document_id": document_id,
        "filename": filename,
        "num_pages": num_pages,
        "model": model_name,
        "pipeline_version": pipeline_version,
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    save_json(
        metadata,
        document_dir / "metadata.json",
    )

    save_json(
        document_structure,
        document_dir / "structure.json",
    )

    save_json(
        semantic_nodes,
        document_dir / "semantic_nodes.json",
    )

    save_json(
        document_tree,
        document_dir / "tree.json",
    )

def load_processed_document(
    document_id: str,
) -> dict:

    """Load all persisted artifacts for a previously processed document."""
    if not document_exists(document_id):
        raise FileNotFoundError(
            f"Processed document not found: "
            f"{document_id}"
        )

    document_dir = get_document_directory(
        document_id
    )

    return {
        "metadata": load_json(
            document_dir / "metadata.json"
        ),
        "structure": load_json(
            document_dir / "structure.json"
        ),
        "semantic_nodes": load_json(
            document_dir / "semantic_nodes.json"
        ),
        "tree": load_json(
            document_dir / "tree.json"
        ),
    }

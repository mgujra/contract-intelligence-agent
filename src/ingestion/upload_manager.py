"""Upload manager for real-time document ingestion.

Handles file validation, chunking, vector store updates, and persistence
when users upload new contract documents through the Streamlit UI.
"""

import re
from datetime import datetime
from pathlib import Path

from langchain_core.documents import Document

from .chunker import chunk_contract, chunks_to_langchain_documents


# Minimum structural markers a valid contract should contain
REQUIRED_MARKERS = [
    r"CONTRACT NUMBER:",
]

# At least one section header should be present
SECTION_MARKERS = [
    r"--- APPLICABLE FAR CLAUSES ---",
    r"--- APPLICABLE DFARS CLAUSES ---",
    r"--- STATEMENT OF WORK ---",
    r"--- CONTRACT LINE ITEMS",
    r"--- CONTRACTOR INFORMATION ---",
    r"--- SUBCONTRACTOR REQUIREMENTS ---",
    r"--- SECURITY REQUIREMENTS ---",
    r"--- SPECIAL CONTRACT PROVISIONS ---",
]


def validate_upload(file_content: str) -> tuple[bool, str]:
    """
    Validate that an uploaded file has the expected contract structure.

    Args:
        file_content: Raw text content of the uploaded file.

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    if not file_content or not file_content.strip():
        return False, "File is empty."

    if len(file_content.strip()) < 100:
        return False, "File is too short to be a valid contract document."

    # Check for required markers
    for marker in REQUIRED_MARKERS:
        if not re.search(marker, file_content):
            return False, (
                f"Missing required field: '{marker.rstrip(':')}'. "
                "Uploaded documents should follow the standard contract format "
                "with a CONTRACT NUMBER field."
            )

    # Check for at least one section header
    has_section = any(
        re.search(marker, file_content) for marker in SECTION_MARKERS
    )
    if not has_section:
        return False, (
            "No recognized contract sections found. "
            "Expected at least one section such as FAR CLAUSES, "
            "STATEMENT OF WORK, or CONTRACT LINE ITEMS."
        )

    return True, ""


def save_uploaded_file(
    file_content: str,
    filename: str,
    save_directory: str | Path,
) -> Path:
    """
    Save an uploaded file to the documents directory.

    If a file with the same name already exists, appends a timestamp
    to avoid overwriting.

    Args:
        file_content: Raw text content.
        filename: Original filename from the uploader.
        save_directory: Directory to save the file in.

    Returns:
        Path to the saved file.
    """
    save_dir = Path(save_directory)
    save_dir.mkdir(parents=True, exist_ok=True)

    save_path = save_dir / filename

    # Avoid overwriting existing files
    if save_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = save_path.stem
        save_path = save_dir / f"{stem}_{timestamp}.txt"

    save_path.write_text(file_content, encoding="utf-8")
    return save_path


def process_upload(
    file_content: str,
    filename: str,
    vector_store,
    save_directory: str | Path = "./data/synthetic/documents",
) -> dict:
    """
    Process an uploaded document through the full ingestion pipeline.

    Steps:
        1. Save file to disk for persistence
        2. Chunk using clause-aware splitter
        3. Convert to LangChain Documents
        4. Add to existing ChromaDB vector store

    Args:
        file_content: Raw text content of the uploaded file.
        filename: Original filename.
        vector_store: Existing Chroma vector store instance.
        save_directory: Where to persist the uploaded file.

    Returns:
        Dict with processing stats:
            - saved_path: Where the file was saved
            - num_chunks: Total chunks created
            - num_vectors_added: Vectors added to store
            - chunk_types: Breakdown by chunk type
            - contract_number: Extracted contract number
    """
    # Step 1: Save to disk
    saved_path = save_uploaded_file(file_content, filename, save_directory)

    # Step 2: Chunk the document
    chunks = chunk_contract(file_content)

    if not chunks:
        return {
            "saved_path": str(saved_path),
            "num_chunks": 0,
            "num_vectors_added": 0,
            "chunk_types": {},
            "contract_number": "UNKNOWN",
            "error": "No chunks could be extracted from the document.",
        }

    # Step 3: Convert to LangChain Documents
    documents = chunks_to_langchain_documents(chunks)

    # Add source_file metadata to each document
    for doc in documents:
        doc.metadata["source_file"] = filename
        doc.metadata["upload_time"] = datetime.now().isoformat()

    # Step 4: Add to vector store
    vector_store.add_documents(documents)

    # Collect chunk type stats
    chunk_types: dict[str, int] = {}
    for chunk in chunks:
        chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1

    contract_number = chunks[0].contract_number if chunks else "UNKNOWN"

    return {
        "saved_path": str(saved_path),
        "num_chunks": len(chunks),
        "num_vectors_added": len(documents),
        "chunk_types": chunk_types,
        "contract_number": contract_number,
    }

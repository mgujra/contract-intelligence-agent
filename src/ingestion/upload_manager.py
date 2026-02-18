"""Upload manager for real-time document ingestion.

Handles file validation, chunking, vector store updates, and persistence
when users upload new contract documents through the Streamlit UI.

Supports two upload paths:
- .txt files: Validated for standard contract format, chunked directly
- .docx files: Parsed via hybrid extraction (regex + LLM), then chunked
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


def validate_upload(file_content: str | bytes, filename: str = "") -> tuple[bool, str]:
    """
    Validate that an uploaded file has the expected format.

    For .txt files: checks for standard contract markers/sections.
    For .docx files: validates as a valid Word document with content.

    Args:
        file_content: Raw text (str for .txt) or raw bytes (bytes for .docx).
        filename: Original filename — used to detect format.

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    ext = Path(filename).suffix.lower() if filename else ""

    if ext == ".docx" or isinstance(file_content, bytes):
        return _validate_docx(file_content)
    else:
        return _validate_txt(file_content)


def _validate_txt(file_content: str) -> tuple[bool, str]:
    """Validate a .txt contract file."""
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


def _validate_docx(file_content: bytes) -> tuple[bool, str]:
    """Validate a .docx file using the docx parser."""
    from .docx_parser import validate_docx
    return validate_docx(file_content)


def save_uploaded_file(
    file_content: str | bytes,
    filename: str,
    save_directory: str | Path,
) -> Path:
    """
    Save an uploaded file to the documents directory.

    If a file with the same name already exists, appends a timestamp
    to avoid overwriting.

    Args:
        file_content: Raw text (str) or raw bytes (bytes).
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
        ext = save_path.suffix or ".txt"
        save_path = save_dir / f"{stem}_{timestamp}{ext}"

    if isinstance(file_content, bytes):
        save_path.write_bytes(file_content)
    else:
        save_path.write_text(file_content, encoding="utf-8")
    return save_path


def process_upload(
    file_content: str,
    filename: str,
    vector_store,
    save_directory: str | Path = "./data/synthetic/documents",
) -> dict:
    """
    Process an uploaded .txt document through the full ingestion pipeline.

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


def process_docx_upload(
    file_bytes: bytes,
    filename: str,
    vector_store,
    save_directory: str | Path = "./data/synthetic/documents",
    json_directory: str | Path = "./data/synthetic",
    mode: str = "mock",
    api_key: str | None = None,
) -> dict:
    """
    Process an uploaded .docx document through the hybrid extraction pipeline.

    Steps:
        1. Save original .docx to disk
        2. Run hybrid extraction (regex + LLM) to get JSON + document_text
        3. Save JSON and text to data directories
        4. Chunk document_text and add to vector store

    Args:
        file_bytes: Raw bytes of the uploaded .docx file.
        filename: Original filename.
        vector_store: Existing Chroma vector store instance.
        save_directory: Where to persist extracted text files.
        json_directory: Where to persist extracted JSON files.
        mode: "mock" or "anthropic" for LLM extraction.
        api_key: Anthropic API key (required for anthropic mode).

    Returns:
        Dict with processing stats and extraction report.
    """
    from .hybrid_extractor import extract_contract_from_docx, save_extraction_results

    # Step 1: Save original .docx
    docx_save_dir = Path(save_directory).parent / "uploads"
    saved_docx = save_uploaded_file(file_bytes, filename, docx_save_dir)

    # Step 2: Run hybrid extraction
    extraction = extract_contract_from_docx(
        file_path_or_bytes=file_bytes,
        filename=filename,
        mode=mode,
        api_key=api_key,
    )

    if not extraction.is_valid:
        return {
            "saved_path": str(saved_docx),
            "num_chunks": 0,
            "num_vectors_added": 0,
            "chunk_types": {},
            "contract_number": "UNKNOWN",
            "error": f"Extraction failed: {extraction.error}",
            "extraction_report": None,
        }

    # Step 3: Save JSON and text files
    saved_paths = save_extraction_results(
        extraction,
        json_directory=json_directory,
        text_directory=save_directory,
    )

    # Step 4: Chunk and index the document_text
    chunks = chunk_contract(extraction.document_text)

    if not chunks:
        return {
            "saved_path": str(saved_docx),
            "json_path": str(saved_paths["json_path"]),
            "text_path": str(saved_paths["text_path"]),
            "num_chunks": 0,
            "num_vectors_added": 0,
            "chunk_types": {},
            "contract_number": extraction.contract_data.get("contract_number", "UNKNOWN"),
            "error": "No chunks could be extracted from the generated text.",
            "extraction_report": _report_to_dict(extraction.report),
        }

    documents = chunks_to_langchain_documents(chunks)

    # Add source metadata
    for doc in documents:
        doc.metadata["source_file"] = filename
        doc.metadata["source_format"] = "docx"
        doc.metadata["upload_time"] = datetime.now().isoformat()
        doc.metadata["extraction_mode"] = mode

    vector_store.add_documents(documents)

    # Collect chunk type stats
    chunk_types: dict[str, int] = {}
    for chunk in chunks:
        chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1

    contract_number = extraction.contract_data.get("contract_number", "UNKNOWN")

    return {
        "saved_path": str(saved_docx),
        "json_path": str(saved_paths["json_path"]),
        "text_path": str(saved_paths["text_path"]),
        "num_chunks": len(chunks),
        "num_vectors_added": len(documents),
        "chunk_types": chunk_types,
        "contract_number": contract_number,
        "extraction_report": _report_to_dict(extraction.report),
    }


def _report_to_dict(report) -> dict:
    """Convert an ExtractionReport to a serializable dict."""
    return {
        "total_fields": report.total_fields,
        "regex_extracted": report.regex_extracted,
        "llm_extracted": report.llm_extracted,
        "defaulted": report.defaulted,
        "confidence_avg": round(report.confidence_avg, 3),
        "warnings": report.warnings,
        "field_sources": report.field_sources,
    }

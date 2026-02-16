"""Document loader for synthetic contract corpus.

Loads contracts from JSON files or the corpus file and prepares them
for the chunking and embedding pipeline.
"""

import json
from pathlib import Path

from langchain_core.documents import Document

from .chunker import chunk_contract, chunks_to_langchain_documents


def load_corpus(corpus_path: str | Path) -> list[dict]:
    """Load the full contract corpus from the _corpus.json file."""
    path = Path(corpus_path)
    if path.is_file():
        with open(path) as f:
            return json.load(f)
    raise FileNotFoundError(f"Corpus file not found: {path}")


def load_contract_documents(data_dir: str | Path) -> list[Document]:
    """
    Load all contract text documents and chunk them for RAG.

    This is the main entry point for the ingestion pipeline:
    1. Reads all .txt files from the documents directory
    2. Applies clause-aware chunking to each document
    3. Returns LangChain Document objects ready for embedding

    Args:
        data_dir: Path to the synthetic data directory containing a 'documents' subfolder

    Returns:
        List of LangChain Document objects with metadata
    """
    docs_dir = Path(data_dir) / "documents"
    if not docs_dir.exists():
        raise FileNotFoundError(
            f"Documents directory not found: {docs_dir}. "
            "Run the contract generator first: python -m src.data_generation.contract_generator"
        )

    all_documents = []
    txt_files = sorted(docs_dir.glob("*.txt"))

    if not txt_files:
        raise FileNotFoundError(f"No .txt files found in {docs_dir}")

    for filepath in txt_files:
        text = filepath.read_text(encoding="utf-8")
        chunks = chunk_contract(text)
        documents = chunks_to_langchain_documents(chunks)

        # Add source file to metadata
        for doc in documents:
            doc.metadata["source_file"] = filepath.name

        all_documents.extend(documents)

    print(f"Loaded {len(txt_files)} contracts -> {len(all_documents)} chunks")
    return all_documents


def get_corpus_stats(data_dir: str | Path) -> dict:
    """Get statistics about the contract corpus."""
    corpus_path = Path(data_dir) / "_corpus.json"
    if not corpus_path.exists():
        return {"error": "Corpus not generated yet"}

    contracts = load_corpus(corpus_path)

    type_counts: dict[str, int] = {}
    agency_counts: dict[str, int] = {}
    total_value = 0.0
    dod_count = 0

    for c in contracts:
        ct = c["contract_type"]
        type_counts[ct] = type_counts.get(ct, 0) + 1

        ag = c["agency"]["code"]
        agency_counts[ag] = agency_counts.get(ag, 0) + 1

        total_value += c["value"]
        if c.get("is_dod"):
            dod_count += 1

    return {
        "total_contracts": len(contracts),
        "total_value": total_value,
        "dod_contracts": dod_count,
        "civilian_contracts": len(contracts) - dod_count,
        "contract_types": type_counts,
        "agencies": agency_counts,
    }

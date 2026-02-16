"""One-command setup pipeline for the Contract Intelligence Agent.

Runs the full data generation and ingestion pipeline:
1. Generates synthetic federal contracts (120 contracts)
2. Chunks documents using clause-aware splitting
3. Creates embeddings and builds the ChromaDB vector store

Usage:
    python run_pipeline.py                    # Generate 120 contracts
    python run_pipeline.py --count 50         # Generate 50 contracts
    python run_pipeline.py --skip-generation  # Skip data gen, just re-index
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def run_pipeline(count: int = 120, skip_generation: bool = False):
    """Run the full pipeline."""
    start_time = time.time()

    data_dir = Path("data/synthetic")
    chroma_dir = Path("data/processed/chroma_db")

    # Step 1: Generate synthetic contracts
    if not skip_generation:
        print("=" * 60)
        print("STEP 1: Generating synthetic federal contracts")
        print("=" * 60)
        from src.data_generation.contract_generator import generate_contracts, save_contracts

        contracts = generate_contracts(count)
        save_contracts(contracts, data_dir)
        print()
    else:
        print("Skipping contract generation (--skip-generation)")
        print()

    # Step 2: Load and chunk documents
    print("=" * 60)
    print("STEP 2: Loading and chunking contract documents")
    print("=" * 60)
    from src.ingestion.document_loader import load_contract_documents

    documents = load_contract_documents(data_dir)

    # Print chunk statistics
    chunk_types: dict[str, int] = {}
    for doc in documents:
        ct = doc.metadata.get("chunk_type", "unknown")
        chunk_types[ct] = chunk_types.get(ct, 0) + 1

    print("\nChunk distribution:")
    for ct, n in sorted(chunk_types.items(), key=lambda x: -x[1]):
        print(f"  {ct}: {n}")
    print()

    # Step 3: Create vector store
    print("=" * 60)
    print("STEP 3: Creating vector store (embedding + indexing)")
    print("=" * 60)
    from src.retrieval.vector_store import create_vector_store

    vector_store = create_vector_store(
        documents=documents,
        persist_directory=chroma_dir,
        collection_name="contract_clauses",
    )
    print()

    # Summary
    elapsed = time.time() - start_time
    print("=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Contracts generated: {count if not skip_generation else 'skipped'}")
    print(f"  Documents chunked: {len(documents)}")
    print(f"  Vectors indexed: {vector_store._collection.count()}")
    print(f"  Time elapsed: {elapsed:.1f}s")
    print()
    print("Next steps:")
    print("  1. Run the Streamlit app: streamlit run app/streamlit_app.py")
    print("  2. Click 'Initialize Agent' in the sidebar")
    print("  3. Start querying contracts!")
    print()
    print("  To use Claude instead of mock mode:")
    print("  1. Copy .env.example to .env")
    print("  2. Set ANTHROPIC_API_KEY in .env")
    print("  3. Select 'anthropic' mode in the sidebar")


def main():
    parser = argparse.ArgumentParser(
        description="Contract Intelligence Agent - Setup Pipeline"
    )
    parser.add_argument(
        "--count", type=int, default=120,
        help="Number of synthetic contracts to generate (default: 120)"
    )
    parser.add_argument(
        "--skip-generation", action="store_true",
        help="Skip contract generation and only re-index existing data"
    )
    args = parser.parse_args()

    run_pipeline(count=args.count, skip_generation=args.skip_generation)


if __name__ == "__main__":
    main()

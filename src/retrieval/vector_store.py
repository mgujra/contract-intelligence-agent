"""Vector store setup and management using ChromaDB.

Handles embedding generation, ChromaDB collection management,
and provides the retrieval interface for the RAG pipeline.
"""

from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document


def get_embedding_function(model_name: str = "all-MiniLM-L6-v2"):
    """Get the embedding function for document vectorization.

    Uses sentence-transformers models that run locally (no API key needed).
    Default model is fast and produces good quality embeddings for retrieval.
    """
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def create_vector_store(
    documents: list[Document],
    persist_directory: str | Path,
    collection_name: str = "contract_clauses",
    embedding_model: str = "all-MiniLM-L6-v2",
) -> Chroma:
    """
    Create and persist a ChromaDB vector store from documents.

    Args:
        documents: List of LangChain Document objects (from the chunker)
        persist_directory: Directory to persist the ChromaDB database
        collection_name: Name of the ChromaDB collection
        embedding_model: HuggingFace model name for embeddings

    Returns:
        Chroma vector store instance
    """
    persist_dir = Path(persist_directory)
    persist_dir.mkdir(parents=True, exist_ok=True)

    embeddings = get_embedding_function(embedding_model)

    print(f"Creating vector store with {len(documents)} documents...")
    print(f"  Embedding model: {embedding_model}")
    print(f"  Persist directory: {persist_dir}")
    print(f"  Collection: {collection_name}")

    # Create in batches to show progress
    batch_size = 100
    vector_store = None

    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(documents) + batch_size - 1) // batch_size
        print(f"  Embedding batch {batch_num}/{total_batches} ({len(batch)} documents)...")

        if vector_store is None:
            vector_store = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                persist_directory=str(persist_dir),
                collection_name=collection_name,
            )
        else:
            vector_store.add_documents(batch)

    if vector_store is None:
        raise ValueError("No documents provided to create vector store")

    print(f"Vector store created with {vector_store._collection.count()} vectors")
    return vector_store


def load_vector_store(
    persist_directory: str | Path,
    collection_name: str = "contract_clauses",
    embedding_model: str = "all-MiniLM-L6-v2",
) -> Chroma:
    """
    Load an existing ChromaDB vector store.

    Args:
        persist_directory: Directory where ChromaDB is persisted
        collection_name: Name of the ChromaDB collection
        embedding_model: Must match the model used during creation

    Returns:
        Chroma vector store instance
    """
    persist_dir = Path(persist_directory)
    if not persist_dir.exists():
        raise FileNotFoundError(
            f"Vector store not found at {persist_dir}. "
            "Run the ingestion pipeline first."
        )

    embeddings = get_embedding_function(embedding_model)

    vector_store = Chroma(
        persist_directory=str(persist_dir),
        embedding_function=embeddings,
        collection_name=collection_name,
    )

    count = vector_store._collection.count()
    print(f"Loaded vector store: {count} vectors in collection '{collection_name}'")
    return vector_store


def get_retriever(
    vector_store: Chroma,
    top_k: int = 5,
    search_type: str = "similarity",
    filter_dict: dict | None = None,
):
    """
    Get a retriever from the vector store.

    Args:
        vector_store: ChromaDB vector store
        top_k: Number of results to retrieve
        search_type: "similarity" or "mmr" (maximal marginal relevance)
        filter_dict: Optional metadata filter (e.g., {"chunk_type": "clause"})

    Returns:
        LangChain retriever
    """
    search_kwargs = {"k": top_k}
    if filter_dict:
        search_kwargs["filter"] = filter_dict

    return vector_store.as_retriever(
        search_type=search_type,
        search_kwargs=search_kwargs,
    )

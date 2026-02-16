"""Application settings loaded from environment variables."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration for the Contract Intelligence Agent."""

    # Project paths
    project_root: Path = Path(__file__).parent.parent
    synthetic_data_dir: Path = Path("./data/synthetic")
    chroma_persist_dir: Path = Path("./data/processed/chroma_db")

    # LLM Configuration
    llm_mode: str = "mock"  # "mock", "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # Embedding Configuration
    embedding_model: str = "all-MiniLM-L6-v2"

    # ChromaDB Configuration
    chroma_collection_name: str = "contract_clauses"

    # Data Generation
    num_contracts: int = 120

    # Retrieval Configuration
    top_k_results: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Application
    app_title: str = "Contract Clause Intelligence Agent"
    app_description: str = "AI-powered federal contract analysis using RAG"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()

"""Contract Intelligence Agent - Core RAG pipeline.

Supports two modes:
- mock: Uses keyword-based response generation (no API key needed)
- anthropic: Uses Claude for production-quality responses

Usage:
    from src.agent.contract_agent import ContractAgent

    agent = ContractAgent(mode="mock")  # or mode="anthropic"
    response = agent.query("What are the CMMC requirements in active contracts?")
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from .prompts import SYSTEM_PROMPT, RAG_PROMPT_TEMPLATE
from .mock_llm import generate_mock_response
from ..retrieval.vector_store import load_vector_store, get_retriever


class ContractAgent:
    """RAG-based contract intelligence agent.

    Retrieves relevant contract clauses and provisions from the vector store
    and generates responses using either a mock LLM or Claude.
    """

    def __init__(
        self,
        mode: str = "mock",
        persist_directory: str = "./data/processed/chroma_db",
        collection_name: str = "contract_clauses",
        embedding_model: str = "all-MiniLM-L6-v2",
        anthropic_api_key: str | None = None,
        anthropic_model: str = "claude-sonnet-4-5-20250929",
        top_k: int = 5,
    ):
        self.mode = mode
        self.top_k = top_k
        self.anthropic_model = anthropic_model

        # Load vector store
        self.vector_store = load_vector_store(
            persist_directory=persist_directory,
            collection_name=collection_name,
            embedding_model=embedding_model,
        )
        self.retriever = get_retriever(self.vector_store, top_k=top_k)

        # Set up LLM chain if in anthropic mode
        self.chain = None
        if mode == "anthropic":
            self._setup_anthropic_chain(anthropic_api_key)

    def _setup_anthropic_chain(self, api_key: str | None):
        """Set up the LangChain RAG chain with Claude."""
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required when mode='anthropic'. "
                "Set it in .env or pass it directly."
            )

        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(
            model=self.anthropic_model,
            api_key=api_key,
            temperature=0,
            max_tokens=2048,
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", RAG_PROMPT_TEMPLATE),
        ])

        def format_docs(docs: list[Document]) -> str:
            formatted = []
            for i, doc in enumerate(docs):
                cn = doc.metadata.get("contract_number", "Unknown")
                section = doc.metadata.get("section", "")
                clause = doc.metadata.get("clause_number", "")
                header = f"[Document {i+1} | Contract: {cn}"
                if clause:
                    header += f" | Clause: {clause}"
                if section:
                    header += f" | Section: {section}"
                header += "]"
                formatted.append(f"{header}\n{doc.page_content}")
            return "\n\n---\n\n".join(formatted)

        self.chain = (
            {"context": self.retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

    def retrieve(self, query: str, filter_dict: dict | None = None) -> list[Document]:
        """Retrieve relevant documents without generating a response.

        Useful for debugging and understanding what the retriever finds.
        """
        if filter_dict:
            retriever = get_retriever(self.vector_store, top_k=self.top_k, filter_dict=filter_dict)
            return retriever.invoke(query)
        return self.retriever.invoke(query)

    def query(self, question: str) -> dict:
        """
        Query the contract intelligence agent.

        Args:
            question: Natural language question about contracts

        Returns:
            Dict with 'answer', 'sources', and 'mode' keys
        """
        # Retrieve relevant documents
        retrieved_docs = self.retriever.invoke(question)

        if self.mode == "mock":
            answer = generate_mock_response(question, retrieved_docs)
        elif self.mode == "anthropic" and self.chain:
            answer = self.chain.invoke(question)
        else:
            answer = "Error: Invalid mode or chain not initialized."

        # Extract source information
        sources = []
        seen = set()
        for doc in retrieved_docs:
            cn = doc.metadata.get("contract_number", "Unknown")
            clause = doc.metadata.get("clause_number", "")
            section = doc.metadata.get("section", "")
            key = f"{cn}|{clause}|{section}"
            if key not in seen:
                seen.add(key)
                sources.append({
                    "contract_number": cn,
                    "clause_number": clause,
                    "clause_title": doc.metadata.get("clause_title", ""),
                    "section": section,
                    "chunk_type": doc.metadata.get("chunk_type", ""),
                    "preview": doc.page_content[:150],
                })

        return {
            "answer": answer,
            "sources": sources,
            "mode": self.mode,
            "num_retrieved": len(retrieved_docs),
        }

    def get_stats(self) -> dict:
        """Get vector store statistics."""
        count = self.vector_store._collection.count()
        return {
            "total_vectors": count,
            "mode": self.mode,
            "model": self.anthropic_model if self.mode == "anthropic" else "mock",
            "top_k": self.top_k,
        }

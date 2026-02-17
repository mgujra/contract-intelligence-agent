"""Contract Intelligence Agent - Core RAG pipeline.

Supports two modes:
- mock: Uses keyword-based response generation (no API key needed)
- anthropic: Uses Claude for production-quality responses

Usage:
    from src.agent.contract_agent import ContractAgent

    agent = ContractAgent(mode="mock")  # or mode="anthropic"
    response = agent.query("What are the CMMC requirements in active contracts?")
"""

import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from .prompts import SYSTEM_PROMPT, RAG_PROMPT_TEMPLATE
from .mock_llm import generate_mock_response
from ..retrieval.vector_store import load_vector_store, get_retriever
from ..ingestion.upload_manager import validate_upload, process_upload


def _extract_value_filter(question: str) -> dict | None:
    """Detect numeric value queries and build a ChromaDB metadata filter.

    Parses natural language questions about contract dollar amounts and
    converts them into ChromaDB $where filters using $gte/$lte operators
    on the funded_amount metadata field.

    Examples:
        "contracts with more than 10 million funded" -> {"funded_amount": {"$gte": 10000000}}
        "funded between 10 and 30 million"          -> {"$and": [{"funded_amount": {"$gte": 10000000}},
                                                                  {"funded_amount": {"$lte": 30000000}}]}
        "contracts under 5M"                        -> {"funded_amount": {"$lte": 5000000}}

    Returns:
        A ChromaDB where-filter dict, or None if the question is not value-based.
    """
    q = question.lower()

    # Only trigger on value/funding-related queries
    value_keywords = [
        "funded", "funding", "million", "billion",
        "value over", "value above", "value below", "value under",
        "value between", "more than", "less than", "greater than",
        "exceeding", "at least", "no more than",
    ]
    if not any(kw in q for kw in value_keywords):
        return None

    def _parse_amount(text: str) -> float | None:
        """Parse a dollar amount from natural language."""
        # Match patterns like: 10 million, 10M, $10M, $10 million, 10m, 5 billion, 5B
        patterns = [
            r"\$?([\d,.]+)\s*(?:billion|b)\b",     # billions
            r"\$?([\d,.]+)\s*(?:million|m|mil)\b",  # millions
            r"\$?([\d,.]+)\s*(?:thousand|k)\b",     # thousands
            r"\$?([\d,.]+)",                        # raw number (assume millions if in context)
        ]

        for i, pattern in enumerate(patterns):
            match = re.search(pattern, text)
            if match:
                try:
                    num = float(match.group(1).replace(",", ""))
                    if i == 0:  # billions
                        return num * 1_000_000_000
                    elif i == 1:  # millions
                        return num * 1_000_000
                    elif i == 2:  # thousands
                        return num * 1_000
                    else:
                        # Raw number — if it's small (< 1000) and the question
                        # mentions million/billion context, scale accordingly
                        if num < 1000 and "million" not in text and "billion" not in text:
                            return num * 1_000_000  # assume millions
                        return num
                except ValueError:
                    continue
        return None

    # "between X and Y"
    between_match = re.search(
        r"between\s+\$?([\d,.]+)\s*(?:million|m|mil|billion|b)?\s+and\s+\$?([\d,.]+)\s*(?:million|m|mil|billion|b)?",
        q,
    )
    if between_match:
        low_text = between_match.group(0).split("and")[0]
        high_text = between_match.group(0).split("and")[1]
        low = _parse_amount(low_text)
        high = _parse_amount(high_text)
        if low and high:
            return {"$and": [
                {"funded_amount": {"$gte": low}},
                {"funded_amount": {"$lte": high}},
            ]}

    # "more than / greater than / over / above / exceeding / at least X"
    gte_match = re.search(
        r"(?:more than|greater than|over|above|exceeding|at least|exceed)\s+\$?([\d,.]+)\s*(?:million|m|mil|billion|b|thousand|k)?",
        q,
    )
    if gte_match:
        amount = _parse_amount(gte_match.group(0))
        if amount:
            return {"funded_amount": {"$gte": amount}}

    # "less than / under / below / no more than X"
    lte_match = re.search(
        r"(?:less than|under|below|no more than)\s+\$?([\d,.]+)\s*(?:million|m|mil|billion|b|thousand|k)?",
        q,
    )
    if lte_match:
        amount = _parse_amount(lte_match.group(0))
        if amount:
            return {"funded_amount": {"$lte": amount}}

    return None


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
        top_k: int = 10,
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

        Automatically detects value-based queries (e.g., "contracts with
        more than $10M funded") and applies ChromaDB metadata filtering
        so numeric comparisons are exact rather than relying on embedding
        similarity, which cannot compare numbers.

        Args:
            question: Natural language question about contracts

        Returns:
            Dict with 'answer', 'sources', 'mode', and 'num_retrieved' keys.
            If a value filter was applied, also includes 'value_filter'.
        """
        # Check if this is a value-based query that needs metadata filtering
        value_filter = _extract_value_filter(question)

        if value_filter:
            # Use a filtered retriever with higher top_k to catch more matches
            filtered_retriever = get_retriever(
                self.vector_store,
                top_k=min(self.top_k * 3, 30),  # cast a wider net for value queries
                filter_dict=value_filter,
            )
            retrieved_docs = filtered_retriever.invoke(question)
        else:
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

        result = {
            "answer": answer,
            "sources": sources,
            "mode": self.mode,
            "num_retrieved": len(retrieved_docs),
        }
        if value_filter:
            result["value_filter"] = str(value_filter)
        return result

    def ingest_document(
        self,
        file_content: str,
        filename: str,
        save_directory: str = "./data/synthetic/documents",
    ) -> dict:
        """
        Ingest a new document into the vector store in real time.

        Validates the document, chunks it, adds to ChromaDB, and refreshes
        the retriever so queries immediately reflect the new content.

        Args:
            file_content: Raw text content of the uploaded file.
            filename: Original filename.
            save_directory: Where to persist the uploaded file on disk.

        Returns:
            Dict with processing stats and validation results.
            Contains 'valid' key (bool) and 'error' key (str) if invalid.
        """
        # Validate first
        is_valid, error_msg = validate_upload(file_content)
        if not is_valid:
            return {"valid": False, "error": error_msg}

        # Process through the pipeline
        result = process_upload(
            file_content=file_content,
            filename=filename,
            vector_store=self.vector_store,
            save_directory=save_directory,
        )

        # Refresh the retriever to include new documents
        self.retriever = get_retriever(self.vector_store, top_k=self.top_k)

        result["valid"] = True
        result["new_total_vectors"] = self.vector_store._collection.count()
        return result

    def get_stats(self) -> dict:
        """Get vector store statistics."""
        count = self.vector_store._collection.count()
        return {
            "total_vectors": count,
            "mode": self.mode,
            "model": self.anthropic_model if self.mode == "anthropic" else "mock",
            "top_k": self.top_k,
        }

"""Unit tests for the mock LLM response generator.

Tests the mock agent's ability to produce structured, relevant responses
based on different query types and retrieved context.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.mock_llm import generate_mock_response


def make_mock_doc(content, metadata=None):
    """Create a mock Document-like object for testing."""

    class MockDoc:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata or {}

    return MockDoc(content, metadata or {})


# ===== Test Fixtures =====

SAMPLE_DOCS = [
    make_mock_doc(
        "DFARS 252.204-7012 - Safeguarding Covered Defense Information [MANDATORY FLOWDOWN]\n"
        "The Contractor shall implement NIST SP 800-171 to provide adequate security.",
        {
            "contract_number": "W911NF-24-C-0001",
            "clause_number": "252.204-7012",
            "clause_title": "Safeguarding Covered Defense Information",
            "chunk_type": "clause",
            "flowdown": True,
        },
    ),
    make_mock_doc(
        "DFARS 252.204-7021 - CMMC Requirements [MANDATORY FLOWDOWN]\n"
        "The Contractor shall have a current CMMC certificate.",
        {
            "contract_number": "W911NF-24-C-0001",
            "clause_number": "252.204-7021",
            "clause_title": "CMMC Requirements",
            "chunk_type": "clause",
            "flowdown": True,
        },
    ),
    make_mock_doc(
        "CLIN 0001: Program Management Support\nType: FFP | Total: $1,500,000.00",
        {
            "contract_number": "W911NF-24-C-0001",
            "chunk_type": "clin",
            "clin_number": "0001",
        },
    ),
    make_mock_doc(
        "Subcontractor: DataForge Analytics Inc\nScope: Cybersecurity support\n"
        "Flowdown Clauses: 252.204-7012, 252.204-7021",
        {
            "contract_number": "W911NF-24-C-0001",
            "chunk_type": "subcontractor",
            "subcontractor_name": "DataForge Analytics Inc",
        },
    ),
]


class TestMockResponseGeneration:
    """Test that mock responses are relevant and well-structured."""

    def test_empty_docs_returns_helpful_message(self):
        response = generate_mock_response("What are the CMMC requirements?", [])
        assert "unable to find" in response.lower() or "could not find" in response.lower()

    def test_flowdown_query_mentions_flowdown(self):
        response = generate_mock_response(
            "What are the mandatory flowdown clauses for subcontractors?",
            SAMPLE_DOCS,
        )
        assert "flowdown" in response.lower()

    def test_cybersecurity_query_mentions_cyber(self):
        response = generate_mock_response(
            "What are the CMMC cybersecurity requirements?",
            SAMPLE_DOCS,
        )
        assert "cybersecurity" in response.lower() or "cmmc" in response.lower()

    def test_clin_query_references_clin(self):
        response = generate_mock_response(
            "Show me the contract line items and pricing",
            SAMPLE_DOCS,
        )
        assert "CLIN" in response or "line item" in response.lower() or "contract" in response.lower()

    def test_compliance_query_mentions_requirements(self):
        response = generate_mock_response(
            "What compliance requirements apply to this contract?",
            SAMPLE_DOCS,
        )
        assert "compliance" in response.lower() or "requirement" in response.lower()

    def test_response_includes_contract_number(self):
        response = generate_mock_response(
            "Tell me about this contract",
            SAMPLE_DOCS,
        )
        assert "W911NF-24-C-0001" in response

    def test_response_includes_mock_mode_notice(self):
        response = generate_mock_response("Any question", SAMPLE_DOCS)
        assert "mock mode" in response.lower()

    def test_response_includes_sources(self):
        response = generate_mock_response("Any question", SAMPLE_DOCS)
        assert "source" in response.lower() or "W911NF" in response

    def test_generic_query_returns_content(self):
        response = generate_mock_response(
            "What is this contract about?",
            SAMPLE_DOCS,
        )
        assert len(response) > 100, "Response should be substantive"

    def test_nist_query_returns_relevant_content(self):
        response = generate_mock_response(
            "What NIST SP 800-171 requirements apply?",
            SAMPLE_DOCS,
        )
        assert "800-171" in response or "nist" in response.lower() or "cybersecurity" in response.lower()


class TestResponseStructure:
    """Test that mock responses have consistent structure."""

    def test_response_is_string(self):
        response = generate_mock_response("test", SAMPLE_DOCS)
        assert isinstance(response, str)

    def test_response_not_empty(self):
        response = generate_mock_response("test", SAMPLE_DOCS)
        assert len(response.strip()) > 0

    def test_response_has_markdown_formatting(self):
        response = generate_mock_response("What are the requirements?", SAMPLE_DOCS)
        assert "**" in response, "Response should use markdown bold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

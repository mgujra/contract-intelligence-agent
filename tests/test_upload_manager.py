"""Tests for the document upload manager.

Tests validation, file saving, and chunking integration for the
real-time document upload feature.
"""

import os
import tempfile

import pytest

from src.ingestion.upload_manager import (
    validate_upload,
    save_uploaded_file,
    process_upload,
)


# --- Test Fixtures ---

VALID_CONTRACT = """
============================================================
SYNTHETIC CONTRACT - FOR AI DEMONSTRATION PURPOSES ONLY
============================================================

CONTRACT NUMBER: W911NF-25-C-TEST
Contract Type: Firm-Fixed-Price (FFP)
Awarding Agency: Department of the Army
Contracting Officer: Jane Smith

--- CONTRACTOR INFORMATION ---
  Prime Contractor: Test Defense Corp
  CAGE Code: 1ABC2
  Business Size: Large Business
  UEI: TESTDUNS12345

--- TOTAL CONTRACT VALUE ---
  Base Value: $2,500,000.00
  Ceiling Value: $3,000,000.00
  Currently Funded: $1,500,000.00

--- STATEMENT OF WORK ---
  The contractor shall provide software development services
  for enterprise AI integration platforms including natural
  language processing and document analysis capabilities.

--- CONTRACT LINE ITEMS (CLINs) ---
  CLIN 0001: Software Development Services
    Type: FFP | Qty: 1 | Unit Price: $1,500,000.00 | Total: $1,500,000.00

  CLIN 0002: System Integration Testing
    Type: FFP | Qty: 1 | Unit Price: $500,000.00 | Total: $500,000.00

--- APPLICABLE FAR CLAUSES ---
  FAR 52.204-21 - Basic Safeguarding of Covered Contractor Information Systems
    Requires basic safeguarding requirements for federal contract information.

  FAR 52.219-8 - Utilization of Small Business Concerns
    Requires good faith effort to use small businesses as subcontractors.

--- APPLICABLE DFARS CLAUSES ---
  DFARS 252.204-7012 - Safeguarding Covered Defense Information
    Requires NIST SP 800-171 compliance for CUI handling. [MANDATORY FLOWDOWN]

--- SUBCONTRACTOR REQUIREMENTS ---
  Subcontractor: SubTest LLC (Small Business)
    CAGE Code: 2DEF3
    Subcontract Value: $400,000.00
    Scope: Data analysis and ML model training
    Flowdown Clauses: FAR 52.204-21, DFARS 252.204-7012

--- SECURITY REQUIREMENTS ---
  - Facility Clearance Level: SECRET
  - Personnel clearance required for all key staff
  - NIST SP 800-171 compliance mandatory

--- SPECIAL CONTRACT PROVISIONS ---
  - Monthly progress reports due by the 5th of each month
  - Quarterly technical review meetings required

--- END OF CONTRACT ---
""".strip()

MINIMAL_VALID_CONTRACT = """
CONTRACT NUMBER: TEST-MINIMAL-001
Contract Type: T&M

--- APPLICABLE FAR CLAUSES ---
  FAR 52.204-21 - Basic Safeguarding
    Basic safeguarding requirements.

--- END OF CONTRACT ---
""".strip()


# --- Validation Tests ---

class TestValidateUpload:
    """Tests for upload validation logic."""

    def test_empty_file_rejected(self):
        is_valid, error = validate_upload("")
        assert not is_valid
        assert "empty" in error.lower()

    def test_whitespace_only_rejected(self):
        is_valid, error = validate_upload("   \n\n  \t  ")
        assert not is_valid
        assert "empty" in error.lower()

    def test_too_short_rejected(self):
        is_valid, error = validate_upload("CONTRACT NUMBER: X\nShort.")
        assert not is_valid
        assert "too short" in error.lower()

    def test_missing_contract_number_rejected(self):
        content = "This is a long document " * 20 + "\n--- APPLICABLE FAR CLAUSES ---\n"
        is_valid, error = validate_upload(content)
        assert not is_valid
        assert "CONTRACT NUMBER" in error

    def test_missing_sections_rejected(self):
        content = "CONTRACT NUMBER: W911NF-25-C-0001\n" + ("Some text. " * 20)
        is_valid, error = validate_upload(content)
        assert not is_valid
        assert "section" in error.lower()

    def test_valid_contract_accepted(self):
        is_valid, error = validate_upload(VALID_CONTRACT)
        assert is_valid
        assert error == ""

    def test_minimal_valid_contract_accepted(self):
        is_valid, error = validate_upload(MINIMAL_VALID_CONTRACT)
        assert is_valid
        assert error == ""

    def test_none_input_rejected(self):
        is_valid, error = validate_upload(None)
        assert not is_valid


# --- File Saving Tests ---

class TestSaveUploadedFile:
    """Tests for file persistence logic."""

    def test_saves_file_to_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_uploaded_file("test content", "test.txt", tmpdir)
            assert path.exists()
            assert path.read_text() == "test content"
            assert path.name == "test.txt"

    def test_creates_directory_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "sub", "dir")
            path = save_uploaded_file("content", "test.txt", nested)
            assert path.exists()

    def test_avoids_overwrite_with_timestamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create first file
            path1 = save_uploaded_file("first", "contract.txt", tmpdir)
            # Create second file with same name
            path2 = save_uploaded_file("second", "contract.txt", tmpdir)

            assert path1 != path2
            assert path1.exists()
            assert path2.exists()
            assert path1.read_text() == "first"
            assert path2.read_text() == "second"
            # Second file should have timestamp suffix
            assert "contract_" in path2.name


# --- Chunking Integration Tests ---

class TestProcessUploadChunking:
    """Tests for the chunking integration (no vector store needed)."""

    def test_valid_contract_produces_chunks(self):
        from src.ingestion.chunker import chunk_contract, chunks_to_langchain_documents

        chunks = chunk_contract(VALID_CONTRACT)
        assert len(chunks) > 0

        # Should find FAR clauses
        clause_chunks = [c for c in chunks if c.chunk_type == "clause"]
        assert len(clause_chunks) >= 2  # At least FAR + DFARS clauses

        # Should find CLINs
        clin_chunks = [c for c in chunks if c.chunk_type == "clin"]
        assert len(clin_chunks) >= 1

        # Should extract contract number
        assert chunks[0].contract_number == "W911NF-25-C-TEST"

    def test_langchain_documents_have_metadata(self):
        from src.ingestion.chunker import chunk_contract, chunks_to_langchain_documents

        chunks = chunk_contract(VALID_CONTRACT)
        docs = chunks_to_langchain_documents(chunks)

        for doc in docs:
            assert "contract_number" in doc.metadata
            assert "section" in doc.metadata
            assert "chunk_type" in doc.metadata

    def test_flowdown_detection(self):
        from src.ingestion.chunker import chunk_contract

        chunks = chunk_contract(VALID_CONTRACT)
        dfars_chunks = [
            c for c in chunks
            if c.chunk_type == "clause" and c.metadata.get("clause_type") == "DFARS"
        ]

        # DFARS 252.204-7012 should be marked as flowdown
        flowdown_chunks = [c for c in dfars_chunks if c.metadata.get("flowdown")]
        assert len(flowdown_chunks) >= 1

    def test_subcontractor_chunks(self):
        from src.ingestion.chunker import chunk_contract

        chunks = chunk_contract(VALID_CONTRACT)
        sub_chunks = [c for c in chunks if c.chunk_type == "subcontractor"]
        assert len(sub_chunks) >= 1

    def test_minimal_contract_produces_chunks(self):
        from src.ingestion.chunker import chunk_contract

        chunks = chunk_contract(MINIMAL_VALID_CONTRACT)
        assert len(chunks) > 0
        assert chunks[0].contract_number == "TEST-MINIMAL-001"

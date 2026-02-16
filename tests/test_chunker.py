"""Unit tests for the clause-aware document chunker.

Tests cover:
- Contract number extraction
- Section splitting
- Individual clause chunking (FAR and DFARS)
- CLIN chunking
- Subcontractor requirement chunking
- Flowdown detection
- Edge cases (empty sections, missing sections)
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.chunker import (
    chunk_contract,
    extract_contract_number,
    split_into_sections,
    chunk_clause_section,
    chunk_clins_section,
    chunk_subcontractor_section,
    ContractChunk,
)


# ===== Fixtures =====

SAMPLE_CONTRACT = """================================================================================
*** SYNTHETIC DATA - FOR PORTFOLIO DEMONSTRATION ONLY ***
================================================================================

CONTRACT NUMBER: W911NF-24-C-0001
CONTRACT TYPE: Firm-Fixed-Price (FFP)
CONTRACTING AGENCY: Department of Defense (DOD)
CONTRACTING OFFICER: Jane Doe

--- CONTRACTOR INFORMATION ---
Contractor: Meridian Defense Technologies
CAGE Code: 5K4M7
Business Size: large
DUNS/UEI: AB12345678

--- TOTAL CONTRACT VALUE ---
Base Period Value: $5,000,000.00
Funded Amount: $3,500,000.00

--- PERIOD OF PERFORMANCE ---
Base Period: 2024-01-01 through 2025-12-31 (24 months)
Option Period 1: 2026-01-01 through 2026-12-31 (12 months)

--- STATEMENT OF WORK ---
Cybersecurity Assessment and Authorization (A&A) services for DOD enterprise systems,
including Risk Management Framework (RMF) implementation, continuous monitoring,
and vulnerability management across classified and unclassified environments.

--- CONTRACT LINE ITEMS (CLINs) ---
  CLIN 0001: Program Management Support
    Type: FFP | Qty: 1 Lot | Unit Price: $1,500,000.00 | Total: $1,500,000.00
  CLIN 0002: Senior Systems Engineer
    Type: FFP | Qty: 1 Lot | Unit Price: $2,000,000.00 | Total: $2,000,000.00
  CLIN 0003: Cloud Infrastructure Services
    Type: Cost-Reimbursable | Qty: 1 Lot | Unit Price: $500,000.00 | Total: $500,000.00

--- APPLICABLE FAR CLAUSES ---
  FAR 52.202-1 - Definitions
    When a solicitation provision or contract clause uses a word or term that is defined in the FAR, the word has the same meaning.

  FAR 52.204-21 - Basic Safeguarding of Covered Contractor Information Systems
    The Contractor shall apply basic safeguarding requirements to protect covered contractor information systems.

  FAR 52.222-26 - Equal Opportunity
    During the performance of this contract, the Contractor agrees not to discriminate against any employee.

--- APPLICABLE DFARS CLAUSES ---
  DFARS 252.204-7012 - Safeguarding Covered Defense Information and Cyber Incident Reporting [MANDATORY FLOWDOWN]
    The Contractor shall implement NIST SP 800-171. Report cyber incidents within 72 hours.

  DFARS 252.204-7021 - Cybersecurity Maturity Model Certification Requirements [MANDATORY FLOWDOWN]
    The Contractor shall have a current CMMC certificate at the required level.

  DFARS 252.227-7013 - Rights in Technical Data - Noncommercial Items
    The Government shall have unlimited rights in technical data developed with Government funds.

--- SUBCONTRACTOR REQUIREMENTS ---
  Subcontractor: DataForge Analytics Inc (CAGE: 3F7P2)
    Business Size: small
    Estimated Value: $750,000.00
    Scope: Cybersecurity assessment and monitoring support
    Flowdown Clauses: 252.204-7012, 252.204-7021

  Subcontractor: SecureNet Consulting LLC (CAGE: 8K1M5)
    Business Size: small
    Estimated Value: $300,000.00
    Scope: Network security engineering
    Flowdown Clauses: 252.204-7012

--- SECURITY REQUIREMENTS ---
  - Contractor personnel must hold active SECRET clearance or higher
  - CMMC Level 2 certification required prior to contract award
  - Compliance with NIST SP 800-171 Rev 2 required

--- SPECIAL CONTRACT PROVISIONS ---
  Key Personnel: Program Manager, Chief Engineer - substitution requires 30-day advance notice
  Earned Value Management System (EVMS) reporting required per DID DI-MGMT-81861A

--- END OF CONTRACT ---
*** SYNTHETIC DATA - FOR PORTFOLIO DEMONSTRATION ONLY ***
"""

MINIMAL_CONTRACT = """CONTRACT NUMBER: TEST-MIN-001
--- APPLICABLE FAR CLAUSES ---
  FAR 52.202-1 - Definitions
    Basic definitions clause.
--- END OF CONTRACT ---
"""


# ===== Tests: Contract Number Extraction =====

class TestContractNumberExtraction:
    def test_extracts_standard_number(self):
        assert extract_contract_number(SAMPLE_CONTRACT) == "W911NF-24-C-0001"

    def test_extracts_from_minimal(self):
        assert extract_contract_number(MINIMAL_CONTRACT) == "TEST-MIN-001"

    def test_returns_unknown_when_missing(self):
        assert extract_contract_number("No contract number here") == "UNKNOWN"

    def test_handles_task_order_number(self):
        text = "CONTRACT NUMBER: W911NF-24-C-0001-TO-0042\nother stuff"
        assert extract_contract_number(text) == "W911NF-24-C-0001-TO-0042"


# ===== Tests: Section Splitting =====

class TestSectionSplitting:
    def test_finds_all_sections(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        section_names = [name for name, _ in sections]

        assert "header" in section_names
        assert "contractor_info" in section_names
        assert "value" in section_names
        assert "period_of_performance" in section_names
        assert "scope_of_work" in section_names
        assert "clins" in section_names
        assert "far_clauses" in section_names
        assert "dfars_clauses" in section_names
        assert "subcontractor_requirements" in section_names
        assert "security_requirements" in section_names
        assert "special_provisions" in section_names

    def test_header_contains_contract_number(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        header = next(text for name, text in sections if name == "header")
        assert "W911NF-24-C-0001" in header

    def test_sow_contains_description(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        sow = next(text for name, text in sections if name == "scope_of_work")
        assert "Cybersecurity Assessment" in sow

    def test_stops_at_end_marker(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        all_text = " ".join(text for _, text in sections)
        assert "END OF CONTRACT" not in all_text

    def test_minimal_contract_has_sections(self):
        sections = split_into_sections(MINIMAL_CONTRACT)
        assert len(sections) >= 2  # header + far_clauses


# ===== Tests: Clause Chunking =====

class TestClauseChunking:
    def test_extracts_individual_far_clauses(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        far_text = next(text for name, text in sections if name == "far_clauses")
        chunks = chunk_clause_section(far_text, "W911NF-24-C-0001", "far")

        assert len(chunks) == 3
        clause_numbers = [c.clause_number for c in chunks]
        assert "52.202-1" in clause_numbers
        assert "52.204-21" in clause_numbers
        assert "52.222-26" in clause_numbers

    def test_extracts_individual_dfars_clauses(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        dfars_text = next(text for name, text in sections if name == "dfars_clauses")
        chunks = chunk_clause_section(dfars_text, "W911NF-24-C-0001", "dfars")

        assert len(chunks) == 3
        clause_numbers = [c.clause_number for c in chunks]
        assert "252.204-7012" in clause_numbers
        assert "252.204-7021" in clause_numbers
        assert "252.227-7013" in clause_numbers

    def test_detects_flowdown_clauses(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        dfars_text = next(text for name, text in sections if name == "dfars_clauses")
        chunks = chunk_clause_section(dfars_text, "W911NF-24-C-0001", "dfars")

        flowdown_chunks = [c for c in chunks if c.metadata.get("flowdown")]
        assert len(flowdown_chunks) == 2

        flowdown_numbers = [c.clause_number for c in flowdown_chunks]
        assert "252.204-7012" in flowdown_numbers
        assert "252.204-7021" in flowdown_numbers

    def test_non_flowdown_clause_not_marked(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        dfars_text = next(text for name, text in sections if name == "dfars_clauses")
        chunks = chunk_clause_section(dfars_text, "W911NF-24-C-0001", "dfars")

        rights_clause = next(c for c in chunks if c.clause_number == "252.227-7013")
        assert not rights_clause.metadata.get("flowdown")

    def test_clause_titles_extracted(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        far_text = next(text for name, text in sections if name == "far_clauses")
        chunks = chunk_clause_section(far_text, "W911NF-24-C-0001", "far")

        definitions_clause = next(c for c in chunks if c.clause_number == "52.202-1")
        assert definitions_clause.clause_title == "Definitions"

    def test_clause_text_preserved(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        far_text = next(text for name, text in sections if name == "far_clauses")
        chunks = chunk_clause_section(far_text, "W911NF-24-C-0001", "far")

        safeguarding = next(c for c in chunks if c.clause_number == "52.204-21")
        assert "safeguarding requirements" in safeguarding.text.lower()


# ===== Tests: CLIN Chunking =====

class TestClinChunking:
    def test_extracts_individual_clins(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        clin_text = next(text for name, text in sections if name == "clins")
        chunks = chunk_clins_section(clin_text, "W911NF-24-C-0001")

        assert len(chunks) == 3

    def test_clin_numbers_in_metadata(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        clin_text = next(text for name, text in sections if name == "clins")
        chunks = chunk_clins_section(clin_text, "W911NF-24-C-0001")

        clin_numbers = [c.metadata.get("clin_number") for c in chunks]
        assert "0001" in clin_numbers
        assert "0002" in clin_numbers
        assert "0003" in clin_numbers

    def test_clin_content_preserved(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        clin_text = next(text for name, text in sections if name == "clins")
        chunks = chunk_clins_section(clin_text, "W911NF-24-C-0001")

        pm_clin = next(c for c in chunks if c.metadata.get("clin_number") == "0001")
        assert "Program Management" in pm_clin.text


# ===== Tests: Subcontractor Chunking =====

class TestSubcontractorChunking:
    def test_extracts_individual_subs(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        sub_text = next(text for name, text in sections if name == "subcontractor_requirements")
        chunks = chunk_subcontractor_section(sub_text, "W911NF-24-C-0001")

        assert len(chunks) == 2

    def test_sub_names_in_metadata(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        sub_text = next(text for name, text in sections if name == "subcontractor_requirements")
        chunks = chunk_subcontractor_section(sub_text, "W911NF-24-C-0001")

        names = [c.metadata.get("subcontractor_name") for c in chunks]
        assert "DataForge Analytics Inc" in names
        assert "SecureNet Consulting LLC" in names

    def test_sub_content_includes_flowdown(self):
        sections = split_into_sections(SAMPLE_CONTRACT)
        sub_text = next(text for name, text in sections if name == "subcontractor_requirements")
        chunks = chunk_subcontractor_section(sub_text, "W911NF-24-C-0001")

        dataforge = next(c for c in chunks if "DataForge" in c.metadata.get("subcontractor_name", ""))
        assert "252.204-7012" in dataforge.text


# ===== Tests: Full Pipeline (chunk_contract) =====

class TestFullChunkPipeline:
    def test_produces_expected_chunk_count(self):
        chunks = chunk_contract(SAMPLE_CONTRACT)
        # header + contractor_info + value + pop + sow + 3 clins + 3 far + 3 dfars + 2 subs + security + special
        assert len(chunks) >= 15

    def test_all_chunks_have_contract_number(self):
        chunks = chunk_contract(SAMPLE_CONTRACT)
        for chunk in chunks:
            assert chunk.contract_number == "W911NF-24-C-0001"

    def test_chunk_types_are_valid(self):
        valid_types = {"header", "general", "clause", "clin", "scope_of_work",
                       "subcontractor", "security_requirements", "special_provisions"}
        chunks = chunk_contract(SAMPLE_CONTRACT)
        for chunk in chunks:
            assert chunk.chunk_type in valid_types, f"Invalid chunk_type: {chunk.chunk_type}"

    def test_no_empty_chunks(self):
        chunks = chunk_contract(SAMPLE_CONTRACT)
        for chunk in chunks:
            assert chunk.text.strip(), f"Empty chunk in section: {chunk.section}"

    def test_clause_chunks_have_numbers(self):
        chunks = chunk_contract(SAMPLE_CONTRACT)
        clause_chunks = [c for c in chunks if c.chunk_type == "clause"]
        for chunk in clause_chunks:
            assert chunk.clause_number is not None, "Clause chunk missing clause_number"
            assert chunk.clause_title is not None, "Clause chunk missing clause_title"

    def test_sow_chunk_contains_description(self):
        chunks = chunk_contract(SAMPLE_CONTRACT)
        sow_chunks = [c for c in chunks if c.chunk_type == "scope_of_work"]
        assert len(sow_chunks) == 1
        assert "Cybersecurity Assessment" in sow_chunks[0].text

    def test_security_chunk_exists(self):
        chunks = chunk_contract(SAMPLE_CONTRACT)
        sec_chunks = [c for c in chunks if c.chunk_type == "security_requirements"]
        assert len(sec_chunks) == 1
        assert "SECRET clearance" in sec_chunks[0].text

    def test_minimal_contract_chunks(self):
        chunks = chunk_contract(MINIMAL_CONTRACT)
        assert len(chunks) >= 2  # header + at least one clause
        clause_chunks = [c for c in chunks if c.chunk_type == "clause"]
        assert len(clause_chunks) == 1
        assert clause_chunks[0].clause_number == "52.202-1"


# ===== Tests: Edge Cases =====

class TestEdgeCases:
    def test_empty_document(self):
        chunks = chunk_contract("")
        assert chunks == [] or all(not c.text.strip() for c in chunks)

    def test_no_clauses_section(self):
        text = """CONTRACT NUMBER: EDGE-001
--- STATEMENT OF WORK ---
Some work description.
--- END OF CONTRACT ---
"""
        chunks = chunk_contract(text)
        assert any(c.chunk_type == "scope_of_work" for c in chunks)

    def test_contract_with_no_dfars(self):
        text = """CONTRACT NUMBER: CIV-001
--- APPLICABLE FAR CLAUSES ---
  FAR 52.202-1 - Definitions
    Basic definitions.
--- APPLICABLE DFARS CLAUSES ---
  No DFARS clauses applicable (non-DoD contract).
--- END OF CONTRACT ---
"""
        chunks = chunk_contract(text)
        far_chunks = [c for c in chunks if c.section == "far_clauses"]
        dfars_chunks = [c for c in chunks if c.section == "dfars_clauses"]
        assert len(far_chunks) == 1
        # DFARS section should have 0 individual clause chunks (just a note)
        dfars_clause_chunks = [c for c in dfars_chunks if c.clause_number is not None]
        assert len(dfars_clause_chunks) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Unit tests for FAR/DFARS clause reference data integrity.

Ensures all clause data is well-formed and complete, which is critical
since the synthetic contract generator depends on this data.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_generation.far_clauses import (
    FAR_CLAUSES,
    DFARS_CLAUSES,
    MANDATORY_FLOWDOWN_CLAUSES,
    NAICS_CODES,
    PSC_CODES,
)


class TestFarClauseDataIntegrity:
    """Verify all FAR clauses have required fields and valid format."""

    def test_all_far_categories_non_empty(self):
        for category, clauses in FAR_CLAUSES.items():
            assert len(clauses) > 0, f"FAR category '{category}' is empty"

    def test_all_far_clauses_have_required_fields(self):
        for category, clauses in FAR_CLAUSES.items():
            for clause in clauses:
                assert "number" in clause, f"Missing 'number' in FAR {category}"
                assert "title" in clause, f"Missing 'title' in FAR {category}"
                assert "text" in clause, f"Missing 'text' in FAR {category}"

    def test_far_clause_numbers_follow_format(self):
        """FAR clauses should be in 52.XXX-XX format."""
        for category, clauses in FAR_CLAUSES.items():
            for clause in clauses:
                num = clause["number"]
                assert num.startswith("52."), (
                    f"FAR clause {num} doesn't start with '52.' in {category}"
                )

    def test_far_clause_text_not_too_short(self):
        for category, clauses in FAR_CLAUSES.items():
            for clause in clauses:
                assert len(clause["text"]) > 30, (
                    f"FAR {clause['number']} text is suspiciously short ({len(clause['text'])} chars)"
                )

    def test_no_duplicate_far_clause_numbers(self):
        all_numbers = []
        for clauses in FAR_CLAUSES.values():
            for clause in clauses:
                all_numbers.append(clause["number"])
        assert len(all_numbers) == len(set(all_numbers)), "Duplicate FAR clause numbers found"


class TestDfarsClauseDataIntegrity:
    """Verify all DFARS clauses have required fields and valid format."""

    def test_all_dfars_categories_non_empty(self):
        for category, clauses in DFARS_CLAUSES.items():
            assert len(clauses) > 0, f"DFARS category '{category}' is empty"

    def test_all_dfars_clauses_have_required_fields(self):
        for category, clauses in DFARS_CLAUSES.items():
            for clause in clauses:
                assert "number" in clause, f"Missing 'number' in DFARS {category}"
                assert "title" in clause, f"Missing 'title' in DFARS {category}"
                assert "text" in clause, f"Missing 'text' in DFARS {category}"

    def test_dfars_clause_numbers_follow_format(self):
        """DFARS clauses should be in 252.XXX-XXXX format."""
        for category, clauses in DFARS_CLAUSES.items():
            for clause in clauses:
                num = clause["number"]
                assert num.startswith("252."), (
                    f"DFARS clause {num} doesn't start with '252.' in {category}"
                )

    def test_no_duplicate_dfars_clause_numbers(self):
        all_numbers = []
        for clauses in DFARS_CLAUSES.values():
            for clause in clauses:
                all_numbers.append(clause["number"])
        assert len(all_numbers) == len(set(all_numbers)), "Duplicate DFARS clause numbers found"

    def test_flowdown_marked_clauses_exist(self):
        """Clauses with flowdown=True should be identifiable."""
        flowdown_clauses = []
        for clauses in DFARS_CLAUSES.values():
            for clause in clauses:
                if clause.get("flowdown"):
                    flowdown_clauses.append(clause["number"])
        assert len(flowdown_clauses) > 0, "No flowdown clauses marked in DFARS data"


class TestMandatoryFlowdownClauses:
    """Verify mandatory flowdown clause references are valid."""

    def test_flowdown_clauses_exist_in_data(self):
        """All mandatory flowdown clause numbers should exist in FAR or DFARS data."""
        all_clause_numbers = set()
        for clauses in FAR_CLAUSES.values():
            for clause in clauses:
                all_clause_numbers.add(clause["number"])
        for clauses in DFARS_CLAUSES.values():
            for clause in clauses:
                all_clause_numbers.add(clause["number"])

        for flowdown in MANDATORY_FLOWDOWN_CLAUSES:
            assert flowdown in all_clause_numbers, (
                f"Mandatory flowdown clause {flowdown} not found in FAR/DFARS data"
            )

    def test_flowdown_list_not_empty(self):
        assert len(MANDATORY_FLOWDOWN_CLAUSES) > 0


class TestReferenceData:
    """Verify NAICS and PSC code data."""

    def test_naics_codes_are_numeric(self):
        for code in NAICS_CODES:
            assert code.isdigit(), f"NAICS code '{code}' is not numeric"

    def test_naics_codes_have_descriptions(self):
        for code, desc in NAICS_CODES.items():
            assert len(desc) > 5, f"NAICS {code} has short description: '{desc}'"

    def test_psc_codes_have_descriptions(self):
        for code, desc in PSC_CODES.items():
            assert len(desc) > 5, f"PSC {code} has short description: '{desc}'"

    def test_minimum_naics_coverage(self):
        assert len(NAICS_CODES) >= 10, "Should have at least 10 NAICS codes"

    def test_minimum_psc_coverage(self):
        assert len(PSC_CODES) >= 10, "Should have at least 10 PSC codes"


class TestOverallDataVolume:
    """Verify sufficient data for realistic contract generation."""

    def test_minimum_far_clauses(self):
        total = sum(len(v) for v in FAR_CLAUSES.values())
        assert total >= 20, f"Only {total} FAR clauses - need at least 20 for realism"

    def test_minimum_dfars_clauses(self):
        total = sum(len(v) for v in DFARS_CLAUSES.values())
        assert total >= 10, f"Only {total} DFARS clauses - need at least 10 for realism"

    def test_minimum_far_categories(self):
        assert len(FAR_CLAUSES) >= 8, "Should have at least 8 FAR categories"

    def test_minimum_dfars_categories(self):
        assert len(DFARS_CLAUSES) >= 5, "Should have at least 5 DFARS categories"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

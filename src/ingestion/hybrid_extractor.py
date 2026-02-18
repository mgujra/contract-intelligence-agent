"""Hybrid contract extractor — orchestrates regex + LLM extraction.

Parses a Word document, runs regex extractors on structured fields,
LLM extractors on freeform fields, merges results, validates against
the JSON schema, and generates both structured JSON and formatted text
for the RAG pipeline.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .docx_parser import extract_full_content, validate_docx
from .regex_extractors import extract_all_regex, DOD_AGENCIES, CONTRACT_TYPES
from .llm_extractors import extract_freeform_fields


# Map contract type codes to full names
CONTRACT_TYPE_NAMES = {v: k for k, v in CONTRACT_TYPES.items() if len(k) > 3}
CONTRACT_TYPE_NAMES.update({
    "FFP": "Firm-Fixed-Price",
    "CPFF": "Cost-Plus-Fixed-Fee",
    "CPAF": "Cost-Plus-Award-Fee",
    "T&M": "Time-and-Materials",
    "LH": "Labor-Hour",
    "IDIQ": "Indefinite Delivery/Indefinite Quantity",
    "BPA": "Blanket Purchase Agreement",
})


@dataclass
class ExtractionReport:
    """Summary of the extraction process."""
    total_fields: int = 0
    regex_extracted: int = 0
    llm_extracted: int = 0
    defaulted: int = 0
    confidence_avg: float = 0.0
    warnings: list[str] = field(default_factory=list)
    field_sources: dict = field(default_factory=dict)  # field -> "regex" | "llm" | "default"


@dataclass
class ExtractionResult:
    """Complete extraction output."""
    contract_data: dict
    document_text: str
    report: ExtractionReport
    is_valid: bool = True
    error: str = ""


def extract_contract_from_docx(
    file_path_or_bytes,
    filename: str,
    mode: str = "mock",
    api_key: str | None = None,
) -> ExtractionResult:
    """Extract structured contract data from a Word document.

    Uses a hybrid approach:
    1. Parse the .docx for text, tables, and structure
    2. Run regex extractors on structured fields (numbers, dates, clauses)
    3. Run LLM extractors on freeform fields (SOW, security, provisions)
    4. Merge results with confidence-based conflict resolution
    5. Validate and fill defaults
    6. Generate document_text for the RAG chunker

    Args:
        file_path_or_bytes: Path to .docx or raw bytes.
        filename: Original filename for metadata.
        mode: "mock" or "anthropic" for LLM extraction.
        api_key: Anthropic API key (required for anthropic mode).

    Returns:
        ExtractionResult with contract_data, document_text, and report.
    """
    report = ExtractionReport()

    # Step 1: Validate and parse the document
    is_valid, error = validate_docx(file_path_or_bytes)
    if not is_valid:
        return ExtractionResult(
            contract_data={},
            document_text="",
            report=report,
            is_valid=False,
            error=error,
        )

    content = extract_full_content(file_path_or_bytes)

    # Step 2: Run regex extractors
    regex_results = extract_all_regex(content["combined_text"], content["tables"])

    # Step 3: Run LLM extractors
    llm_results = extract_freeform_fields(
        content["combined_text"],
        mode=mode,
        api_key=api_key,
    )

    # Step 4: Merge into contract schema
    contract = _merge_results(regex_results, llm_results, report)

    # Step 5: Fill defaults and validate
    contract = _fill_defaults(contract, filename, report)

    # Step 6: Generate document_text
    document_text = _generate_document_text(contract)

    # Calculate report stats
    confidences = []
    for field_name, result in regex_results.items():
        if result.confidence > 0:
            confidences.append(result.confidence)
    if llm_results.get("confidence", 0) > 0:
        confidences.append(llm_results["confidence"])
    report.confidence_avg = sum(confidences) / len(confidences) if confidences else 0.0
    report.total_fields = report.regex_extracted + report.llm_extracted + report.defaulted

    return ExtractionResult(
        contract_data=contract,
        document_text=document_text,
        report=report,
        is_valid=True,
    )


def _merge_results(regex_results: dict, llm_results: dict, report: ExtractionReport) -> dict:
    """Merge regex and LLM extraction results into contract schema."""
    contract = {}

    # Structured fields from regex (prefer high-confidence regex)
    def _get_regex(field_name, min_confidence=0.5):
        result = regex_results.get(field_name)
        if result and result.value is not None and result.confidence >= min_confidence:
            report.regex_extracted += 1
            report.field_sources[field_name] = "regex"
            return result.value
        return None

    # Core fields from regex
    contract["contract_number"] = _get_regex("contract_number") or "UNKNOWN"
    contract["contract_type"] = _get_regex("contract_type") or "FFP"
    contract["contract_type_name"] = CONTRACT_TYPE_NAMES.get(
        contract["contract_type"], contract["contract_type"]
    )

    # Agency
    agency = _get_regex("agency")
    if agency:
        contract["agency"] = agency
    else:
        contract["agency"] = {"code": "UNKNOWN", "name": "Unknown Agency"}

    contract["contracting_officer"] = _get_regex("contracting_officer") or ""

    # Contractor info
    contractor = {
        "name": _get_regex("contractor_name") or "Unknown Contractor",
        "cage": _get_regex("cage") or "",
        "size": _get_regex("size") or "unknown",
        "uei": _get_regex("uei") or "",
    }
    contract["contractor"] = contractor

    # Codes
    contract["naics_code"] = _get_regex("naics_code") or ""
    contract["psc_code"] = _get_regex("psc_code") or ""
    contract["idiq_vehicle"] = None
    contract["parent_idiq"] = None

    # Financial values
    contract["value"] = _get_regex("value") or 0.0
    contract["ceiling_value"] = _get_regex("ceiling_value")
    contract["funded_amount"] = _get_regex("funded_amount") or contract["value"]

    # Period of performance
    pop = {
        "base_period_start": _get_regex("base_period_start") or "",
        "base_period_end": _get_regex("base_period_end") or "",
        "base_period_months": _get_regex("base_period_months") or 12,
    }
    option_result = regex_results.get("option_periods")
    if option_result and option_result.value:
        pop["option_periods"] = option_result.value
        report.regex_extracted += 1
        report.field_sources["option_periods"] = "regex"
    else:
        pop["option_periods"] = []
    contract["period_of_performance"] = pop

    # CLINs
    clins = _get_regex("clins")
    contract["clins"] = clins if clins else []

    # Clauses
    far = _get_regex("far_clauses")
    dfars = _get_regex("dfars_clauses")
    contract["clauses"] = {
        "far": far if far else [],
        "dfars": dfars if dfars else [],
    }

    # Subcontractors
    subs = _get_regex("subcontractors")
    contract["subcontractor_requirements"] = subs if subs else []

    # Freeform fields from LLM
    contract["scope_of_work"] = llm_results.get("scope_of_work") or ""
    if contract["scope_of_work"]:
        report.llm_extracted += 1
        report.field_sources["scope_of_work"] = "llm"

    contract["security_requirements"] = llm_results.get("security_requirements", [])
    if contract["security_requirements"]:
        report.llm_extracted += 1
        report.field_sources["security_requirements"] = "llm"

    contract["special_provisions"] = llm_results.get("special_provisions", [])
    if contract["special_provisions"]:
        report.llm_extracted += 1
        report.field_sources["special_provisions"] = "llm"

    contract["domain"] = llm_results.get("domain")

    return contract


def _fill_defaults(contract: dict, filename: str, report: ExtractionReport) -> dict:
    """Fill in required defaults for missing fields and add metadata."""

    # Contract number fallback from filename
    if contract.get("contract_number") == "UNKNOWN":
        stem = Path(filename).stem
        if len(stem) > 5:
            contract["contract_number"] = stem
            report.warnings.append(
                f"Contract number not found in text; using filename: {stem}"
            )
        report.defaulted += 1
        report.field_sources["contract_number"] = "default"

    # Determine if DoD
    agency_code = contract.get("agency", {}).get("code", "")
    contract["is_dod"] = agency_code in DOD_AGENCIES

    # Metadata
    contract["synthetic"] = False  # Real uploaded document
    contract["id"] = hash(contract["contract_number"]) % 100000

    # Warnings for important missing fields
    if not contract.get("contracting_officer"):
        report.warnings.append("Contracting officer name not found")
        report.defaulted += 1
        report.field_sources.setdefault("contracting_officer", "default")

    if not contract.get("value") or contract["value"] == 0.0:
        report.warnings.append("Contract dollar value not found")
        report.defaulted += 1
        report.field_sources.setdefault("value", "default")

    if not contract.get("clins"):
        report.warnings.append("No CLINs found — contract may be a summary document")

    if not contract.get("scope_of_work"):
        report.warnings.append("Scope of work not found — try 'anthropic' mode for better extraction")
        report.defaulted += 1
        report.field_sources.setdefault("scope_of_work", "default")
        contract["scope_of_work"] = ""

    pop = contract.get("period_of_performance", {})
    if not pop.get("base_period_start"):
        report.warnings.append("Period of performance dates not found")

    return contract


def _generate_document_text(contract: dict) -> str:
    """Generate formatted text matching the existing RAG pipeline format.

    This replicates the format from contract_to_document() in
    contract_generator.py so the chunker processes it identically.
    """
    lines = []

    lines.append(f"CONTRACT NUMBER: {contract.get('contract_number', 'UNKNOWN')}")
    if contract.get("parent_idiq"):
        lines.append(f"PARENT IDIQ CONTRACT: {contract['parent_idiq']}")
    lines.append(
        f"CONTRACT TYPE: {contract.get('contract_type_name', '')} "
        f"({contract.get('contract_type', '')})"
    )
    agency = contract.get("agency", {})
    lines.append(
        f"CONTRACTING AGENCY: {agency.get('name', 'Unknown')} "
        f"({agency.get('code', '')})"
    )
    lines.append(f"CONTRACTING OFFICER: {contract.get('contracting_officer', '')}")
    lines.append("")

    # Contractor info
    lines.append("--- CONTRACTOR INFORMATION ---")
    contractor = contract.get("contractor", {})
    lines.append(f"Contractor: {contractor.get('name', 'Unknown')}")
    if contractor.get("cage"):
        lines.append(f"CAGE Code: {contractor['cage']}")
    lines.append(f"Business Size: {contractor.get('size', 'unknown')}")
    if contractor.get("uei"):
        lines.append(f"DUNS/UEI: {contractor['uei']}")
    lines.append("")

    if contract.get("idiq_vehicle"):
        lines.append(f"CONTRACT VEHICLE: {contract['idiq_vehicle']}")
        lines.append("")

    if contract.get("naics_code"):
        lines.append(f"NAICS CODE: {contract['naics_code']}")
    if contract.get("psc_code"):
        lines.append(f"PSC CODE: {contract['psc_code']}")
    if contract.get("naics_code") or contract.get("psc_code"):
        lines.append("")

    # Values
    lines.append("--- TOTAL CONTRACT VALUE ---")
    value = contract.get("value", 0)
    if value:
        lines.append(f"Base Period Value: ${value:,.2f}")
    if contract.get("ceiling_value"):
        lines.append(f"Contract Ceiling: ${contract['ceiling_value']:,.2f}")
    funded = contract.get("funded_amount", 0)
    if funded:
        lines.append(f"Funded Amount: ${funded:,.2f}")
    lines.append("")

    # Period of performance
    lines.append("--- PERIOD OF PERFORMANCE ---")
    pop = contract.get("period_of_performance", {})
    if pop.get("base_period_start"):
        lines.append(
            f"Base Period: {pop['base_period_start']} through {pop.get('base_period_end', 'TBD')} "
            f"({pop.get('base_period_months', '?')} months)"
        )
    for opt in pop.get("option_periods", []):
        lines.append(
            f"Option Period {opt['option_number']}: {opt['start_date']} through {opt['end_date']} "
            f"({opt.get('months', '?')} months)"
        )
    lines.append("")

    # SOW
    lines.append("--- STATEMENT OF WORK ---")
    lines.append(contract.get("scope_of_work", "Not available."))
    lines.append("")

    # CLINs
    lines.append("--- CONTRACT LINE ITEMS (CLINs) ---")
    for clin in contract.get("clins", []):
        lines.append(f"  CLIN {clin['clin_number']}: {clin['description']}")
        lines.append(
            f"    Type: {clin.get('type', 'FFP')} | Qty: {clin.get('quantity', 1)} "
            f"{clin.get('unit', 'Lot')} | Unit Price: ${clin.get('unit_price', 0):,.2f} "
            f"| Total: ${clin.get('total_price', 0):,.2f}"
        )
    if not contract.get("clins"):
        lines.append("  No CLINs extracted.")
    lines.append("")

    # FAR clauses
    lines.append("--- APPLICABLE FAR CLAUSES ---")
    for clause in contract.get("clauses", {}).get("far", []):
        lines.append(f"  FAR {clause['number']} - {clause.get('title', '')}")
        if clause.get("text"):
            lines.append(f"    {clause['text']}")
        lines.append("")
    if not contract.get("clauses", {}).get("far"):
        lines.append("  No FAR clauses extracted.")
        lines.append("")

    # DFARS clauses
    lines.append("--- APPLICABLE DFARS CLAUSES ---")
    dfars = contract.get("clauses", {}).get("dfars", [])
    if dfars:
        for clause in dfars:
            flowdown = " [MANDATORY FLOWDOWN]" if clause.get("flowdown") else ""
            lines.append(f"  DFARS {clause['number']} - {clause.get('title', '')}{flowdown}")
            if clause.get("text"):
                lines.append(f"    {clause['text']}")
            lines.append("")
    else:
        lines.append("  No DFARS clauses extracted.")
        lines.append("")

    # Subcontractors
    if contract.get("subcontractor_requirements"):
        lines.append("--- SUBCONTRACTOR REQUIREMENTS ---")
        for sub in contract["subcontractor_requirements"]:
            cage_str = f" (CAGE: {sub['cage_code']})" if sub.get("cage_code") else ""
            lines.append(f"  Subcontractor: {sub['subcontractor_name']}{cage_str}")
            lines.append(f"    Business Size: {sub.get('business_size', 'unknown')}")
            if sub.get("estimated_value"):
                lines.append(f"    Estimated Value: ${sub['estimated_value']:,.2f}")
            if sub.get("scope"):
                lines.append(f"    Scope: {sub['scope']}")
            if sub.get("flowdown_clauses"):
                lines.append(f"    Flowdown Clauses: {', '.join(sub['flowdown_clauses'])}")
            lines.append("")

    # Security requirements
    if contract.get("security_requirements"):
        lines.append("--- SECURITY REQUIREMENTS ---")
        for req in contract["security_requirements"]:
            lines.append(f"  - {req}")
        lines.append("")

    # Special provisions
    if contract.get("special_provisions"):
        lines.append("--- SPECIAL CONTRACT PROVISIONS ---")
        for prov in contract["special_provisions"]:
            lines.append(f"  {prov}")
        lines.append("")

    lines.append("--- END OF CONTRACT ---")

    return "\n".join(lines)


def save_extraction_results(
    result: ExtractionResult,
    json_directory: str | Path = "./data/synthetic",
    text_directory: str | Path = "./data/synthetic/documents",
) -> dict[str, Path]:
    """Save extracted contract data as JSON and text files.

    Args:
        result: ExtractionResult from extract_contract_from_docx.
        json_directory: Where to save the .json file.
        text_directory: Where to save the .txt file.

    Returns:
        Dict with 'json_path' and 'text_path'.
    """
    contract_number = result.contract_data.get("contract_number", "UNKNOWN")

    json_dir = Path(json_directory)
    text_dir = Path(text_directory)
    json_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_path = json_dir / f"{contract_number}.json"
    # Add document_text to the JSON (matching synthetic format)
    json_data = {**result.contract_data, "document_text": result.document_text}
    json_path.write_text(json.dumps(json_data, indent=2, default=str), encoding="utf-8")

    # Save text
    text_path = text_dir / f"{contract_number}.txt"
    text_path.write_text(result.document_text, encoding="utf-8")

    return {"json_path": json_path, "text_path": text_path}

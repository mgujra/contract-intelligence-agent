"""Rule-based extractors for structured contract fields.

Uses regex patterns to extract well-formatted fields from contract text:
contract numbers, dollar values, dates, FAR/DFARS clause numbers, CLINs,
contractor information, and more.

Each extractor returns a dict with 'value', 'confidence', and 'field_name'.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExtractionResult:
    """Result from a single field extraction."""
    value: object = None
    confidence: float = 0.0
    field_name: str = ""
    raw_match: str = ""


# Known federal agencies for matching
KNOWN_AGENCIES = {
    "Department of Defense": "DOD",
    "Department of the Army": "ARMY",
    "U.S. Army": "ARMY",
    "United States Army": "ARMY",
    "U.S. Navy": "NAVY",
    "United States Navy": "NAVY",
    "U.S. Air Force": "USAF",
    "United States Air Force": "USAF",
    "Department of Homeland Security": "DHS",
    "Department of Veterans Affairs": "VA",
    "Department of Energy": "DOE",
    "National Aeronautics and Space Administration": "NASA",
    "Defense Information Systems Agency": "DISA",
    "Defense Logistics Agency": "DLA",
    "General Services Administration": "GSA",
    "Department of Health and Human Services": "HHS",
    "Department of Justice": "DOJ",
    "Department of the Interior": "DOI",
    "Department of State": "DOS",
    "Department of Transportation": "DOT",
    "Department of Commerce": "DOC",
    "Department of Education": "ED",
    "Department of Labor": "DOL",
    "Department of Treasury": "TREAS",
}

CONTRACT_TYPES = {
    "Firm-Fixed-Price": "FFP",
    "FFP": "FFP",
    "Cost-Plus-Fixed-Fee": "CPFF",
    "CPFF": "CPFF",
    "Cost-Plus-Award-Fee": "CPAF",
    "CPAF": "CPAF",
    "Time-and-Materials": "T&M",
    "T&M": "T&M",
    "Labor-Hour": "LH",
    "LH": "LH",
    "Indefinite Delivery/Indefinite Quantity": "IDIQ",
    "IDIQ": "IDIQ",
    "Blanket Purchase Agreement": "BPA",
    "BPA": "BPA",
    "Cost-Plus-Incentive-Fee": "CPIF",
    "CPIF": "CPIF",
    "Fixed-Price Incentive": "FPI",
    "FPI": "FPI",
}

DOD_AGENCIES = {"DOD", "ARMY", "NAVY", "USAF", "DISA", "DLA"}


def extract_contract_number(text: str) -> ExtractionResult:
    """Extract contract number from text."""
    # Pattern 1: Explicit label
    labeled = re.search(
        r"CONTRACT\s+(?:NUMBER|NO|#)[:\s]+([A-Z0-9][A-Z0-9\-]{5,25})",
        text, re.IGNORECASE
    )
    if labeled:
        return ExtractionResult(
            value=labeled.group(1).strip(),
            confidence=0.95,
            field_name="contract_number",
            raw_match=labeled.group(0),
        )

    # Pattern 2: Standard federal contract number format
    # e.g., W911NF-25-D-0001, FA8650-24-C-1234, N00024-22-C-6615
    standard = re.search(
        r"\b([A-Z]{1,6}\d{2,4}[-][0-9]{2}[-][A-Z][-][0-9]{4,6})\b",
        text,
    )
    if standard:
        return ExtractionResult(
            value=standard.group(1),
            confidence=0.85,
            field_name="contract_number",
            raw_match=standard.group(0),
        )

    # Pattern 3: DOE-style (DE-AC05-23-D-1215)
    doe = re.search(
        r"\b(DE[-][A-Z]{2}\d{2}[-]\d{2}[-][A-Z][-]\d{4})\b",
        text,
    )
    if doe:
        return ExtractionResult(
            value=doe.group(1),
            confidence=0.85,
            field_name="contract_number",
            raw_match=doe.group(0),
        )

    return ExtractionResult(field_name="contract_number")


def extract_dollar_values(text: str) -> dict[str, ExtractionResult]:
    """Extract dollar values with field context.

    Returns dict mapping field names to ExtractionResults:
    'value' (base), 'ceiling_value', 'funded_amount'.
    """
    results = {}

    # Field-specific patterns with context labels
    field_patterns = [
        (r"(?:Base\s+Period\s+Value|Total\s+Contract\s+Value|Contract\s+Value|Base\s+Value)[:\s]*\$?([\d,]+(?:\.\d{2})?)", "value"),
        (r"(?:Contract\s+Ceiling|Ceiling\s+Value|Ceiling\s+Amount|Maximum\s+Value)[:\s]*\$?([\d,]+(?:\.\d{2})?)", "ceiling_value"),
        (r"(?:Funded\s+Amount|Amount\s+Funded|Obligated\s+Amount|Funded\s+Value)[:\s]*\$?([\d,]+(?:\.\d{2})?)", "funded_amount"),
    ]

    for pattern, field_name in field_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                amount = float(match.group(1).replace(",", ""))
                results[field_name] = ExtractionResult(
                    value=amount,
                    confidence=0.9,
                    field_name=field_name,
                    raw_match=match.group(0),
                )
            except ValueError:
                pass

    # Fallback: find any dollar amounts and assign to 'value' if no specific match
    if not results:
        all_amounts = re.findall(r"\$\s*([\d,]+(?:\.\d{2})?)", text)
        if all_amounts:
            try:
                amounts = [float(a.replace(",", "")) for a in all_amounts]
                # Largest amount is likely the base value
                max_amount = max(amounts)
                results["value"] = ExtractionResult(
                    value=max_amount,
                    confidence=0.5,
                    field_name="value",
                    raw_match=f"${max_amount:,.2f}",
                )
            except ValueError:
                pass

    return results


def extract_dates(text: str) -> dict[str, ExtractionResult]:
    """Extract dates and period of performance information."""
    results = {}

    # ISO format dates with context
    pop_pattern = re.search(
        r"(?:Base\s+Period|Period\s+of\s+Performance)[:\s]*"
        r"(\d{4}[-/]\d{2}[-/]\d{2})\s+(?:through|to|-)\s+(\d{4}[-/]\d{2}[-/]\d{2})",
        text, re.IGNORECASE
    )
    if pop_pattern:
        results["base_period_start"] = ExtractionResult(
            value=pop_pattern.group(1).replace("/", "-"),
            confidence=0.9,
            field_name="base_period_start",
            raw_match=pop_pattern.group(0),
        )
        results["base_period_end"] = ExtractionResult(
            value=pop_pattern.group(2).replace("/", "-"),
            confidence=0.9,
            field_name="base_period_end",
            raw_match=pop_pattern.group(0),
        )

    # US format: Month DD, YYYY or MM/DD/YYYY
    us_pop = re.search(
        r"(?:Base\s+Period|Period\s+of\s+Performance)[:\s]*"
        r"(\d{1,2}/\d{1,2}/\d{2,4})\s+(?:through|to|-)\s+(\d{1,2}/\d{1,2}/\d{2,4})",
        text, re.IGNORECASE
    )
    if us_pop and "base_period_start" not in results:
        for i, group_idx in enumerate([1, 2]):
            date_str = us_pop.group(group_idx)
            try:
                parts = date_str.split("/")
                month, day = int(parts[0]), int(parts[1])
                year = int(parts[2])
                if year < 100:
                    year += 2000
                iso_date = f"{year:04d}-{month:02d}-{day:02d}"
                field_name = "base_period_start" if i == 0 else "base_period_end"
                results[field_name] = ExtractionResult(
                    value=iso_date,
                    confidence=0.85,
                    field_name=field_name,
                    raw_match=us_pop.group(0),
                )
            except (ValueError, IndexError):
                pass

    # Duration in months
    months_match = re.search(r"\((\d+)\s+months?\)", text, re.IGNORECASE)
    if months_match:
        results["base_period_months"] = ExtractionResult(
            value=int(months_match.group(1)),
            confidence=0.85,
            field_name="base_period_months",
            raw_match=months_match.group(0),
        )

    # Option periods
    option_periods = []
    option_matches = re.finditer(
        r"Option\s+(?:Period\s+)?(\d+)[:\s]*"
        r"(\d{4}[-/]\d{2}[-/]\d{2})\s+(?:through|to|-)\s+(\d{4}[-/]\d{2}[-/]\d{2})"
        r"(?:\s*\((\d+)\s+months?\))?",
        text, re.IGNORECASE
    )
    for m in option_matches:
        opt = {
            "option_number": int(m.group(1)),
            "start_date": m.group(2).replace("/", "-"),
            "end_date": m.group(3).replace("/", "-"),
        }
        if m.group(4):
            opt["months"] = int(m.group(4))
        else:
            opt["months"] = 12  # default
        option_periods.append(opt)

    if option_periods:
        results["option_periods"] = ExtractionResult(
            value=option_periods,
            confidence=0.85,
            field_name="option_periods",
        )

    return results


def extract_far_clauses(text: str) -> ExtractionResult:
    """Extract FAR clause numbers and titles."""
    clauses = []

    # FAR clause with title: FAR 52.xxx-xxx - Title
    far_pattern = re.finditer(
        r"(?:FAR\s+)?(52\.\d{3}[-]\d{1,4})\s*[-\u2013\u2014]\s*(.+?)(?:\n|$)",
        text,
    )
    for match in far_pattern:
        clause = {
            "number": match.group(1),
            "title": match.group(2).strip(),
            "text": "",  # Will be filled by LLM or left empty
            "prescription": "",
        }
        clauses.append(clause)

    # Just clause numbers without titles (e.g., in flowdown lists)
    if not clauses:
        far_nums = re.findall(r"\b(52\.\d{3}[-]\d{1,4})\b", text)
        for num in set(far_nums):
            clauses.append({
                "number": num,
                "title": "",
                "text": "",
                "prescription": "",
            })

    confidence = 0.9 if clauses else 0.0
    return ExtractionResult(
        value=clauses,
        confidence=confidence,
        field_name="far_clauses",
    )


def extract_dfars_clauses(text: str) -> ExtractionResult:
    """Extract DFARS clause numbers and titles."""
    clauses = []

    # DFARS clause with title
    dfars_pattern = re.finditer(
        r"(?:DFARS\s+)?(252\.\d{3}[-]\d{1,4})\s*[-\u2013\u2014]\s*(.+?)(?:\n|$)",
        text,
    )
    for match in dfars_pattern:
        is_flowdown = bool(re.search(
            r"(?:MANDATORY\s+FLOWDOWN|shall\s+flow\s+down|apply\s+to\s+subcontract)",
            text[max(0, match.start() - 200):match.end() + 200],
            re.IGNORECASE,
        ))
        clause = {
            "number": match.group(1),
            "title": match.group(2).strip(),
            "text": "",
            "prescription": "",
        }
        if is_flowdown:
            clause["flowdown"] = True
        clauses.append(clause)

    # Just numbers
    if not clauses:
        dfars_nums = re.findall(r"\b(252\.\d{3}[-]\d{1,4})\b", text)
        for num in set(dfars_nums):
            clauses.append({
                "number": num,
                "title": "",
                "text": "",
                "prescription": "",
            })

    confidence = 0.9 if clauses else 0.0
    return ExtractionResult(
        value=clauses,
        confidence=confidence,
        field_name="dfars_clauses",
    )


def extract_clins(text: str, tables: list[dict] | None = None) -> ExtractionResult:
    """Extract Contract Line Items from text or tables."""
    clins = []

    # Try table-based extraction first (more reliable)
    if tables:
        for table in tables:
            headers_lower = [h.lower() for h in table["headers"]]
            # Check if this looks like a CLIN table
            clin_indicators = ["clin", "line item", "description", "quantity", "price"]
            if any(ind in " ".join(headers_lower) for ind in clin_indicators):
                for row in table["rows"]:
                    clin = _parse_clin_row(row, table["headers"])
                    if clin:
                        clins.append(clin)

    # Text-based extraction
    if not clins:
        clin_pattern = re.finditer(
            r"CLIN\s+(\d{4})[:\s]+(.+?)(?:\n|$)"
            r"(?:\s*Type:\s*(.+?)\s*\|\s*Qty:\s*([\d.]+)\s*(\w+)\s*\|\s*Unit\s*Price:\s*\$([\d,.]+)\s*\|\s*Total:\s*\$([\d,.]+))?",
            text, re.IGNORECASE
        )
        for m in clin_pattern:
            clin = {
                "clin_number": m.group(1),
                "description": m.group(2).strip(),
                "type": m.group(3).strip() if m.group(3) else "FFP",
                "quantity": int(float(m.group(4))) if m.group(4) else 1,
                "unit": m.group(5) if m.group(5) else "Lot",
                "unit_price": float(m.group(6).replace(",", "")) if m.group(6) else 0.0,
                "total_price": float(m.group(7).replace(",", "")) if m.group(7) else 0.0,
            }
            clins.append(clin)

    confidence = 0.85 if clins else 0.0
    return ExtractionResult(
        value=clins,
        confidence=confidence,
        field_name="clins",
    )


def _parse_clin_row(row: dict, headers: list[str]) -> dict | None:
    """Parse a single CLIN table row into a structured dict."""
    clin = {}

    for header, value in row.items():
        hl = header.lower()
        vl = value.strip()
        if not vl:
            continue

        if "clin" in hl or "line item" in hl:
            # Extract just the number
            num_match = re.search(r"(\d{4})", vl)
            clin["clin_number"] = num_match.group(1) if num_match else vl
        elif "description" in hl or "title" in hl:
            clin["description"] = vl
        elif "type" in hl:
            clin["type"] = vl
        elif "qty" in hl or "quantity" in hl:
            try:
                clin["quantity"] = int(float(vl.replace(",", "")))
            except ValueError:
                clin["quantity"] = 1
        elif "unit" in hl and "price" not in hl:
            clin["unit"] = vl
        elif "unit price" in hl or "unit cost" in hl:
            try:
                clin["unit_price"] = float(vl.replace("$", "").replace(",", ""))
            except ValueError:
                clin["unit_price"] = 0.0
        elif "total" in hl or "amount" in hl or "extended" in hl:
            try:
                clin["total_price"] = float(vl.replace("$", "").replace(",", ""))
            except ValueError:
                clin["total_price"] = 0.0

    if "clin_number" not in clin and "description" not in clin:
        return None

    # Fill defaults
    clin.setdefault("clin_number", "0000")
    clin.setdefault("description", "")
    clin.setdefault("type", "FFP")
    clin.setdefault("quantity", 1)
    clin.setdefault("unit", "Lot")
    clin.setdefault("unit_price", 0.0)
    clin.setdefault("total_price", 0.0)

    return clin


def extract_contractor_info(text: str) -> dict[str, ExtractionResult]:
    """Extract contractor name, CAGE code, business size, UEI."""
    results = {}

    # Contractor name
    name_match = re.search(
        r"(?:Contractor|Prime\s+Contractor|Vendor|Offeror)[:\s]+(.+?)(?:\n|$)",
        text, re.IGNORECASE,
    )
    if name_match:
        results["contractor_name"] = ExtractionResult(
            value=name_match.group(1).strip(),
            confidence=0.85,
            field_name="contractor_name",
            raw_match=name_match.group(0),
        )

    # CAGE code
    cage_match = re.search(r"CAGE\s*(?:Code|#)?[:\s]*([A-Z0-9]{5})", text, re.IGNORECASE)
    if cage_match:
        results["cage"] = ExtractionResult(
            value=cage_match.group(1),
            confidence=0.9,
            field_name="cage",
            raw_match=cage_match.group(0),
        )

    # UEI / DUNS
    uei_match = re.search(
        r"(?:UEI|DUNS|DUNS/UEI|SAM\s+UEI)[:\s]*([A-Z0-9]{8,13})",
        text, re.IGNORECASE,
    )
    if uei_match:
        results["uei"] = ExtractionResult(
            value=uei_match.group(1),
            confidence=0.9,
            field_name="uei",
            raw_match=uei_match.group(0),
        )

    # Business size
    size_match = re.search(
        r"(?:Business\s+Size|Size\s+Standard|Size\s+Status)[:\s]*(small|large|mid|8\(?a\)?|sdvosb|wosb|hubzone|small\s+business|large\s+business)",
        text, re.IGNORECASE,
    )
    if size_match:
        size = size_match.group(1).strip().lower()
        # Normalize
        if "small business" in size:
            size = "small"
        elif "large business" in size:
            size = "large"
        elif "8" in size:
            size = "8a"
        results["size"] = ExtractionResult(
            value=size,
            confidence=0.85,
            field_name="size",
            raw_match=size_match.group(0),
        )

    return results


def extract_agency(text: str) -> ExtractionResult:
    """Extract contracting agency name and code."""
    # Explicit label
    agency_match = re.search(
        r"(?:CONTRACTING\s+AGENCY|Awarding\s+Agency|Issuing\s+Office)[:\s]+(.+?)(?:\n|$)",
        text, re.IGNORECASE,
    )
    if agency_match:
        agency_text = agency_match.group(1).strip()
        # Try to match against known agencies
        for name, code in KNOWN_AGENCIES.items():
            if name.lower() in agency_text.lower():
                return ExtractionResult(
                    value={"code": code, "name": name},
                    confidence=0.9,
                    field_name="agency",
                    raw_match=agency_match.group(0),
                )
        # Unknown agency
        return ExtractionResult(
            value={"code": "OTHER", "name": agency_text},
            confidence=0.7,
            field_name="agency",
            raw_match=agency_match.group(0),
        )

    # Check for agency names anywhere in text
    for name, code in KNOWN_AGENCIES.items():
        if name.lower() in text.lower():
            return ExtractionResult(
                value={"code": code, "name": name},
                confidence=0.6,
                field_name="agency",
            )

    return ExtractionResult(field_name="agency")


def extract_contract_type(text: str) -> ExtractionResult:
    """Extract contract type (FFP, CPFF, T&M, etc.)."""
    # Explicit label
    type_match = re.search(
        r"CONTRACT\s+TYPE[:\s]+(.+?)(?:\n|$)",
        text, re.IGNORECASE,
    )
    if type_match:
        type_text = type_match.group(1).strip()
        for name, code in CONTRACT_TYPES.items():
            if name.lower() in type_text.lower():
                return ExtractionResult(
                    value=code,
                    confidence=0.9,
                    field_name="contract_type",
                    raw_match=type_match.group(0),
                )

    # Search for type keywords anywhere
    for name, code in CONTRACT_TYPES.items():
        if len(name) > 3 and name.lower() in text.lower():
            return ExtractionResult(
                value=code,
                confidence=0.6,
                field_name="contract_type",
            )

    return ExtractionResult(field_name="contract_type")


def extract_contracting_officer(text: str) -> ExtractionResult:
    """Extract contracting officer name."""
    co_match = re.search(
        r"(?:CONTRACTING\s+OFFICER|Contracting\s+Officer\s+Representative|COR)[:\s]+([A-Z][a-z]*\.?\s+(?:[A-Z][a-z]+[\s.]*)+)",
        text, re.IGNORECASE,
    )
    if co_match:
        return ExtractionResult(
            value=co_match.group(1).strip(),
            confidence=0.85,
            field_name="contracting_officer",
            raw_match=co_match.group(0),
        )
    return ExtractionResult(field_name="contracting_officer")


def extract_naics_code(text: str) -> ExtractionResult:
    """Extract NAICS code."""
    match = re.search(r"NAICS\s*(?:CODE|#)?[:\s]*(\d{6})", text, re.IGNORECASE)
    if match:
        return ExtractionResult(
            value=match.group(1),
            confidence=0.9,
            field_name="naics_code",
            raw_match=match.group(0),
        )
    return ExtractionResult(field_name="naics_code")


def extract_psc_code(text: str) -> ExtractionResult:
    """Extract PSC (Product/Service) code."""
    match = re.search(r"PSC\s*(?:CODE|#)?[:\s]*([A-Z]\d{3})", text, re.IGNORECASE)
    if match:
        return ExtractionResult(
            value=match.group(1),
            confidence=0.9,
            field_name="psc_code",
            raw_match=match.group(0),
        )
    return ExtractionResult(field_name="psc_code")


def extract_subcontractors(text: str) -> ExtractionResult:
    """Extract subcontractor requirements from text."""
    subs = []

    sub_pattern = re.finditer(
        r"Subcontractor[:\s]+(.+?)(?:\(CAGE[:\s]*([A-Z0-9]{5})\))?"
        r"(?:.*?Business\s+Size[:\s]*(\w+))?"
        r"(?:.*?(?:Estimated\s+)?Value[:\s]*\$([\d,.]+))?"
        r"(?:.*?Scope[:\s]*(.+?)(?:\n|$))?",
        text, re.IGNORECASE | re.DOTALL,
    )
    for m in sub_pattern:
        sub = {
            "subcontractor_name": m.group(1).strip().rstrip("("),
            "cage_code": m.group(2) or "",
            "business_size": (m.group(3) or "small").lower(),
            "estimated_value": float(m.group(4).replace(",", "")) if m.group(4) else 0.0,
            "scope": m.group(5).strip() if m.group(5) else "",
            "flowdown_clauses": [],
        }
        subs.append(sub)

    # Extract flowdown clauses near subcontractor sections
    flowdown_match = re.search(
        r"Flowdown\s+Clauses?[:\s]*((?:(?:52|252)\.\d{3}[-]\d{1,4}[,\s]*)+)",
        text, re.IGNORECASE,
    )
    if flowdown_match and subs:
        clause_nums = re.findall(r"((?:52|252)\.\d{3}[-]\d{1,4})", flowdown_match.group(1))
        # Assign to last subcontractor (or all if only one)
        for sub in subs:
            sub["flowdown_clauses"] = clause_nums

    confidence = 0.8 if subs else 0.0
    return ExtractionResult(
        value=subs,
        confidence=confidence,
        field_name="subcontractors",
    )


def extract_all_regex(text: str, tables: list[dict] | None = None) -> dict[str, ExtractionResult]:
    """Run all regex extractors and return combined results.

    Args:
        text: Full document text.
        tables: Optional list of extracted tables for CLIN parsing.

    Returns:
        Dict mapping field names to ExtractionResults.
    """
    results = {}

    # Single-value extractors
    results["contract_number"] = extract_contract_number(text)
    results["agency"] = extract_agency(text)
    results["contract_type"] = extract_contract_type(text)
    results["contracting_officer"] = extract_contracting_officer(text)
    results["naics_code"] = extract_naics_code(text)
    results["psc_code"] = extract_psc_code(text)
    results["far_clauses"] = extract_far_clauses(text)
    results["dfars_clauses"] = extract_dfars_clauses(text)
    results["clins"] = extract_clins(text, tables)
    results["subcontractors"] = extract_subcontractors(text)

    # Multi-value extractors
    for name, result in extract_dollar_values(text).items():
        results[name] = result

    for name, result in extract_dates(text).items():
        results[name] = result

    for name, result in extract_contractor_info(text).items():
        results[name] = result

    return results

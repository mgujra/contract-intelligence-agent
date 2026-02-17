"""Clause-aware document chunker for federal contracts.

Unlike generic text splitters, this chunker understands the structure of
federal contracts and splits documents along meaningful boundaries:
- Contract sections (CONTRACTOR INFORMATION, CLAUSES, CLINs, etc.)
- Individual FAR/DFARS clauses
- Subcontractor requirement blocks

This preserves context within each chunk and enables more accurate retrieval.
"""

import re
from dataclasses import dataclass, field


@dataclass
class ContractChunk:
    """A chunk of a contract document with metadata."""
    text: str
    contract_number: str
    section: str
    chunk_type: str  # "header", "clause", "clin", "sow", "subcontractor", "security", "general"
    clause_number: str | None = None
    clause_title: str | None = None
    metadata: dict = field(default_factory=dict)


# Section patterns in our synthetic contract format
SECTION_PATTERNS = [
    (r"--- (CONTRACTOR INFORMATION) ---", "contractor_info"),
    (r"--- (TOTAL CONTRACT VALUE) ---", "value"),
    (r"--- (PERIOD OF PERFORMANCE) ---", "period_of_performance"),
    (r"--- (STATEMENT OF WORK) ---", "scope_of_work"),
    (r"--- (CONTRACT LINE ITEMS \(CLINs\)) ---", "clins"),
    (r"--- (APPLICABLE FAR CLAUSES) ---", "far_clauses"),
    (r"--- (APPLICABLE DFARS CLAUSES) ---", "dfars_clauses"),
    (r"--- (SUBCONTRACTOR REQUIREMENTS) ---", "subcontractor_requirements"),
    (r"--- (SECURITY REQUIREMENTS) ---", "security_requirements"),
    (r"--- (SPECIAL CONTRACT PROVISIONS) ---", "special_provisions"),
]

# Pattern to identify individual clauses within FAR/DFARS sections
CLAUSE_PATTERN = re.compile(
    r"^\s+((?:FAR|DFARS)\s+[\d.]+-[\d]+)\s+-\s+(.+?)$",
    re.MULTILINE,
)


def extract_contract_number(text: str) -> str:
    """Extract contract number from document text."""
    match = re.search(r"CONTRACT NUMBER:\s*(.+?)$", text, re.MULTILINE)
    return match.group(1).strip() if match else "UNKNOWN"


def _parse_dollar_amount(raw: str) -> float | None:
    """Parse a dollar amount string like '$18,172,478.80' into a float."""
    match = re.search(r"\$[\d,]+(?:\.\d+)?", raw)
    if match:
        try:
            return float(match.group().replace("$", "").replace(",", ""))
        except ValueError:
            return None
    return None


def _format_value_label(amount: float) -> str:
    """Format a dollar amount into a human-readable label like '$18.2M'."""
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    elif amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    else:
        return f"${amount:,.0f}"


def extract_contract_metadata(text: str) -> dict:
    """Extract key contract-level metadata from the document.

    These fields are propagated to EVERY chunk so that queries about
    contracting officers, agencies, contract types, or dollar values
    can match any chunk from the relevant contract.

    Numeric value fields (funded_amount, base_value, ceiling_value) are
    stored as floats for ChromaDB metadata filtering ($gte/$lte), and a
    human-readable value_label (e.g., '$18.2M funded') is included so
    the embedding model can capture contract scale semantically.
    """
    metadata = {}

    # Text fields from the header
    text_patterns = {
        "contracting_officer": r"CONTRACTING OFFICER:\s*(.+?)$",
        "contracting_agency": r"CONTRACTING AGENCY:\s*(.+?)$",
        "contract_type": r"CONTRACT TYPE:\s*(.+?)$",
    }

    for key, pattern in text_patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            metadata[key] = match.group(1).strip()

    # Numeric value fields from the TOTAL CONTRACT VALUE section.
    # Stored as floats so ChromaDB can filter with $gte/$lte operators,
    # enabling queries like "contracts funded between $10M and $30M".
    value_patterns = {
        "funded_amount": r"Funded Amount:\s*(.+?)$",
        "base_value": r"Base Period Value:\s*(.+?)$",
        "ceiling_value": r"Contract Ceiling:\s*(.+?)$",
    }

    for key, pattern in value_patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            amount = _parse_dollar_amount(match.group(1))
            if amount is not None:
                metadata[key] = amount

    # Build a human-readable value label for the context prefix.
    # This gives the embedding model a semantic signal about contract scale
    # (e.g., "$18.2M funded") so value-related queries match better.
    funded = metadata.get("funded_amount")
    base = metadata.get("base_value")
    ceiling = metadata.get("ceiling_value")

    if funded:
        metadata["value_label"] = f"{_format_value_label(funded)} funded"
    elif base:
        metadata["value_label"] = f"{_format_value_label(base)} base value"
    elif ceiling:
        metadata["value_label"] = f"{_format_value_label(ceiling)} ceiling"

    return metadata


def build_context_prefix(contract_number: str, contract_metadata: dict) -> str:
    """Build a context line to prepend to each chunk for better embeddings.

    This ensures the embedding model captures contract-level context
    (officer, agency, type, value) in every chunk's vector, enabling
    semantic retrieval on metadata queries like 'Which contracts does
    X manage?' or 'contracts funded over $10M'.
    """
    parts = [f"Contract: {contract_number}"]

    if contract_metadata.get("contracting_officer"):
        parts.append(f"Officer: {contract_metadata['contracting_officer']}")
    if contract_metadata.get("contracting_agency"):
        parts.append(f"Agency: {contract_metadata['contracting_agency']}")
    if contract_metadata.get("contract_type"):
        parts.append(f"Type: {contract_metadata['contract_type']}")
    if contract_metadata.get("value_label"):
        parts.append(f"Value: {contract_metadata['value_label']}")

    return "[" + " | ".join(parts) + "]\n"


def split_into_sections(text: str) -> list[tuple[str, str]]:
    """Split a contract document into named sections."""
    sections = []
    lines = text.split("\n")

    # Extract header (everything before the first section)
    header_lines = []
    current_section_name = "header"
    current_section_lines: list[str] = []

    for line in lines:
        matched = False
        for pattern, section_name in SECTION_PATTERNS:
            if re.search(pattern, line):
                # Save previous section
                if current_section_lines:
                    sections.append((current_section_name, "\n".join(current_section_lines)))
                current_section_name = section_name
                current_section_lines = [line]
                matched = True
                break

        if not matched:
            if line.strip() == "--- END OF CONTRACT ---":
                break
            current_section_lines.append(line)

    # Don't forget the last section
    if current_section_lines:
        sections.append((current_section_name, "\n".join(current_section_lines)))

    return sections


def chunk_clause_section(
    section_text: str,
    contract_number: str,
    clause_type: str,  # "far" or "dfars"
) -> list[ContractChunk]:
    """Split a clause section into individual clause chunks."""
    chunks = []

    # Find all clause positions
    clause_positions = []
    for match in CLAUSE_PATTERN.finditer(section_text):
        clause_positions.append({
            "start": match.start(),
            "number": match.group(1).strip(),
            "title": match.group(2).strip(),
        })

    if not clause_positions:
        # No individual clauses found, return whole section
        if section_text.strip():
            chunks.append(ContractChunk(
                text=section_text.strip(),
                contract_number=contract_number,
                section=f"{clause_type}_clauses",
                chunk_type="clause",
            ))
        return chunks

    # Extract each clause with its full text
    for i, pos in enumerate(clause_positions):
        end = clause_positions[i + 1]["start"] if i + 1 < len(clause_positions) else len(section_text)
        clause_text = section_text[pos["start"]:end].strip()

        # Remove trailing empty lines
        clause_text = clause_text.rstrip()

        chunks.append(ContractChunk(
            text=clause_text,
            contract_number=contract_number,
            section=f"{clause_type}_clauses",
            chunk_type="clause",
            clause_number=pos["number"].replace("FAR ", "").replace("DFARS ", ""),
            clause_title=pos["title"],
            metadata={
                "clause_type": clause_type.upper(),
                "flowdown": "[MANDATORY FLOWDOWN]" in clause_text,
            },
        ))

    return chunks


def chunk_clins_section(section_text: str, contract_number: str) -> list[ContractChunk]:
    """Split CLIN section into individual CLIN chunks."""
    chunks = []
    clin_pattern = re.compile(r"^\s+CLIN\s+(\d+):", re.MULTILINE)

    positions = list(clin_pattern.finditer(section_text))
    if not positions:
        if section_text.strip():
            chunks.append(ContractChunk(
                text=section_text.strip(),
                contract_number=contract_number,
                section="clins",
                chunk_type="clin",
            ))
        return chunks

    for i, match in enumerate(positions):
        end = positions[i + 1].start() if i + 1 < len(positions) else len(section_text)
        clin_text = section_text[match.start():end].strip()
        chunks.append(ContractChunk(
            text=clin_text,
            contract_number=contract_number,
            section="clins",
            chunk_type="clin",
            metadata={"clin_number": match.group(1)},
        ))

    return chunks


def chunk_subcontractor_section(section_text: str, contract_number: str) -> list[ContractChunk]:
    """Split subcontractor section into individual sub requirements."""
    chunks = []
    sub_pattern = re.compile(r"^\s+Subcontractor:\s+(.+?)$", re.MULTILINE)

    positions = list(sub_pattern.finditer(section_text))
    if not positions:
        if section_text.strip():
            chunks.append(ContractChunk(
                text=section_text.strip(),
                contract_number=contract_number,
                section="subcontractor_requirements",
                chunk_type="subcontractor",
            ))
        return chunks

    for i, match in enumerate(positions):
        end = positions[i + 1].start() if i + 1 < len(positions) else len(section_text)
        sub_text = section_text[match.start():end].strip()
        chunks.append(ContractChunk(
            text=sub_text,
            contract_number=contract_number,
            section="subcontractor_requirements",
            chunk_type="subcontractor",
            metadata={"subcontractor_name": match.group(1).split("(")[0].strip()},
        ))

    return chunks


def chunk_contract(text: str) -> list[ContractChunk]:
    """
    Chunk a contract document using clause-aware splitting.

    This is the main entry point. It:
    1. Extracts the contract number and contract-level metadata
    2. Splits into major sections
    3. Applies section-specific chunking strategies
    4. Propagates contract metadata to every chunk for better retrieval
    5. Returns a list of ContractChunk objects with rich metadata
    """
    contract_number = extract_contract_number(text)
    contract_metadata = extract_contract_metadata(text)
    context_prefix = build_context_prefix(contract_number, contract_metadata)
    sections = split_into_sections(text)
    chunks = []

    for section_name, section_text in sections:
        if not section_text.strip():
            continue

        if section_name == "far_clauses":
            chunks.extend(chunk_clause_section(section_text, contract_number, "far"))

        elif section_name == "dfars_clauses":
            chunks.extend(chunk_clause_section(section_text, contract_number, "dfars"))

        elif section_name == "clins":
            chunks.extend(chunk_clins_section(section_text, contract_number))

        elif section_name == "subcontractor_requirements":
            chunks.extend(chunk_subcontractor_section(section_text, contract_number))

        else:
            # For header, SOW, security, special provisions - keep as single chunks
            chunks.append(ContractChunk(
                text=context_prefix + section_text.strip(),
                contract_number=contract_number,
                section=section_name,
                chunk_type=section_name if section_name in ["scope_of_work", "security_requirements"] else "general",
            ))

    # Propagate contract-level metadata and context prefix to ALL chunks.
    # This ensures every chunk carries the officer, agency, and type so that
    # metadata-style queries (e.g., "Who is the officer on contract X?") can
    # match any chunk from the relevant contract.
    for chunk in chunks:
        chunk.metadata.update(contract_metadata)
        # Add context prefix to chunks that don't already have it
        if not chunk.text.startswith("[Contract:"):
            chunk.text = context_prefix + chunk.text

    return chunks


def chunks_to_langchain_documents(chunks: list[ContractChunk]):
    """Convert ContractChunks to LangChain Document objects."""
    from langchain_core.documents import Document

    documents = []
    for chunk in chunks:
        metadata = {
            "contract_number": chunk.contract_number,
            "section": chunk.section,
            "chunk_type": chunk.chunk_type,
            **chunk.metadata,
        }
        if chunk.clause_number:
            metadata["clause_number"] = chunk.clause_number
        if chunk.clause_title:
            metadata["clause_title"] = chunk.clause_title

        documents.append(Document(page_content=chunk.text, metadata=metadata))

    return documents

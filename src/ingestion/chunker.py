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
    1. Extracts the contract number
    2. Splits into major sections
    3. Applies section-specific chunking strategies
    4. Returns a list of ContractChunk objects with rich metadata
    """
    contract_number = extract_contract_number(text)
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
            # Prepend contract number context for non-header sections
            context_prefix = f"[Contract: {contract_number}]\n" if section_name != "header" else ""
            chunks.append(ContractChunk(
                text=context_prefix + section_text.strip(),
                contract_number=contract_number,
                section=section_name,
                chunk_type=section_name if section_name in ["scope_of_work", "security_requirements"] else "general",
            ))

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

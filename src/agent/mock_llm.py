"""Mock LLM for testing the pipeline without API keys.

Provides keyword-based response generation that simulates an LLM's behavior
for the contract analysis domain. Good enough for testing the full pipeline
and UI without incurring API costs.
"""

import re
from langchain_core.documents import Document


def generate_mock_response(question: str, context_docs: list[Document]) -> str:
    """Generate a mock response based on keyword matching and retrieved context.

    This provides realistic-looking responses for testing by:
    1. Extracting key information from retrieved documents
    2. Formatting it in a structured, professional way
    3. Adding relevant framing based on the question type
    """
    question_lower = question.lower()

    # Extract contract numbers and clauses from context
    contract_numbers = set()
    clause_refs = set()
    for doc in context_docs:
        cn = doc.metadata.get("contract_number", "")
        if cn and cn != "UNKNOWN":
            contract_numbers.add(cn)
        cl = doc.metadata.get("clause_number", "")
        if cl:
            clause_refs.add(cl)

    # Build context summary from retrieved docs
    context_snippets = []
    for i, doc in enumerate(context_docs[:5]):
        snippet = doc.page_content[:300].strip()
        source = doc.metadata.get("contract_number", "Unknown")
        section = doc.metadata.get("section", "general")
        context_snippets.append(f"[Source: {source}, Section: {section}]\n{snippet}")

    if not context_docs:
        return (
            "I was unable to find relevant contract documents to answer your question. "
            "Please try rephrasing your query or asking about specific FAR/DFARS clauses, "
            "contract provisions, or compliance requirements."
        )

    # Determine response type based on question keywords
    response_parts = []

    if any(w in question_lower for w in ["flowdown", "subcontract", "flow down", "flow-down"]):
        response_parts.append("**Flowdown Requirements Analysis**\n")
        response_parts.append(
            f"Based on the retrieved contract documents ({', '.join(list(contract_numbers)[:3])}), "
            "here are the relevant flowdown requirements:\n\n"
        )
        for doc in context_docs:
            if doc.metadata.get("flowdown") or "flowdown" in doc.page_content.lower():
                clause = doc.metadata.get("clause_number", "")
                title = doc.metadata.get("clause_title", "")
                response_parts.append(f"- **{clause}** ({title}): Mandatory flowdown to subcontractors\n")
                response_parts.append(f"  {doc.page_content[:200].strip()}\n\n")

    elif any(w in question_lower for w in ["cmmc", "cybersecurity", "nist", "800-171", "cyber"]):
        response_parts.append("**Cybersecurity Requirements Summary**\n")
        response_parts.append(
            f"Analyzing cybersecurity provisions across {len(contract_numbers)} contract(s):\n\n"
        )
        for doc in context_docs:
            if any(kw in doc.page_content.lower() for kw in ["cmmc", "nist", "cyber", "800-171"]):
                cn = doc.metadata.get("contract_number", "Unknown")
                response_parts.append(f"**Contract {cn}:**\n{doc.page_content[:250].strip()}\n\n")

    elif any(w in question_lower for w in ["officer", "contracting officer", "who manage", "who is the"]):
        response_parts.append("**Contracting Officer Analysis**\n")
        # Use metadata to find officer matches
        officer_contracts = {}
        for doc in context_docs:
            officer = doc.metadata.get("contracting_officer", "")
            cn = doc.metadata.get("contract_number", "Unknown")
            agency = doc.metadata.get("contracting_agency", "")
            if officer:
                if officer not in officer_contracts:
                    officer_contracts[officer] = []
                if cn not in officer_contracts[officer]:
                    officer_contracts[officer].append((cn, agency))

        if officer_contracts:
            for officer, contracts in officer_contracts.items():
                response_parts.append(f"\n**{officer}** is the contracting officer on:\n")
                for cn, agency in contracts:
                    agency_short = agency.split("(")[0].strip() if agency else ""
                    response_parts.append(f"- Contract **{cn}** ({agency_short})\n")
        else:
            response_parts.append(
                "No contracting officer information found in the retrieved documents. "
                "Try searching for a specific officer name.\n"
            )

    elif any(w in question_lower for w in ["agency", "department", "awarded by"]):
        response_parts.append("**Agency / Department Analysis**\n")
        agency_contracts = {}
        for doc in context_docs:
            agency = doc.metadata.get("contracting_agency", "")
            cn = doc.metadata.get("contract_number", "Unknown")
            if agency and cn not in agency_contracts.get(agency, []):
                agency_contracts.setdefault(agency, []).append(cn)

        if agency_contracts:
            for agency, contracts in agency_contracts.items():
                response_parts.append(f"\n**{agency}:**\n")
                for cn in contracts:
                    response_parts.append(f"- {cn}\n")
        else:
            response_parts.append("No agency information found in the retrieved documents.\n")

    elif any(w in question_lower for w in ["compliance", "require", "obligat"]):
        response_parts.append("**Compliance Requirements**\n")
        response_parts.append(
            f"The following compliance requirements were identified across "
            f"{len(contract_numbers)} contract(s):\n\n"
        )
        for i, doc in enumerate(context_docs[:5]):
            cn = doc.metadata.get("contract_number", "Unknown")
            clause = doc.metadata.get("clause_number", "N/A")
            response_parts.append(f"{i+1}. **{clause}** (Contract: {cn})\n")
            response_parts.append(f"   {doc.page_content[:200].strip()}\n\n")

    elif any(w in question_lower for w in ["funded", "fund", "million", "value over", "value between", "value above", "value below", "budget", "spend"]):
        response_parts.append("**Contract Value / Funding Analysis**\n")
        # Collect unique contracts with their value metadata
        value_contracts = {}
        for doc in context_docs:
            cn = doc.metadata.get("contract_number", "Unknown")
            if cn not in value_contracts:
                funded = doc.metadata.get("funded_amount")
                base = doc.metadata.get("base_value")
                ceiling = doc.metadata.get("ceiling_value")
                agency = doc.metadata.get("contracting_agency", "")
                ctype = doc.metadata.get("contract_type", "")
                if funded or base or ceiling:
                    value_contracts[cn] = {
                        "funded": funded,
                        "base": base,
                        "ceiling": ceiling,
                        "agency": agency,
                        "type": ctype,
                    }

        if value_contracts:
            # Sort by funded amount descending
            sorted_contracts = sorted(
                value_contracts.items(),
                key=lambda x: x[1].get("funded") or x[1].get("base") or 0,
                reverse=True,
            )
            for cn, vals in sorted_contracts:
                funded_str = f"${vals['funded']:,.2f}" if vals.get("funded") else "N/A"
                base_str = f"${vals['base']:,.2f}" if vals.get("base") else "N/A"
                agency_short = vals["agency"].split("(")[0].strip() if vals["agency"] else ""
                response_parts.append(
                    f"- **{cn}** ({agency_short})\n"
                    f"  Funded: {funded_str} | Base Value: {base_str} | Type: {vals['type']}\n\n"
                )
        else:
            response_parts.append("No contract value information found in retrieved documents.\n")

    elif any(w in question_lower for w in ["clin", "line item", "price", "cost"]):
        response_parts.append("**Contract Line Item Information**\n")
        for doc in context_docs:
            if doc.metadata.get("chunk_type") == "clin" or "CLIN" in doc.page_content:
                cn = doc.metadata.get("contract_number", "Unknown")
                response_parts.append(f"**Contract {cn}:**\n{doc.page_content[:300].strip()}\n\n")

    else:
        # Generic response
        response_parts.append(f"**Analysis Results**\n")
        response_parts.append(
            f"Based on {len(context_docs)} relevant document sections from "
            f"{len(contract_numbers)} contract(s), here is the relevant information:\n\n"
        )
        for i, doc in enumerate(context_docs[:5]):
            cn = doc.metadata.get("contract_number", "Unknown")
            section = doc.metadata.get("section", "general")
            response_parts.append(f"**[{cn} - {section}]**\n{doc.page_content[:250].strip()}\n\n")

    # Add citations
    if contract_numbers:
        response_parts.append("\n---\n*Sources: " + ", ".join(sorted(contract_numbers)[:5]) + "*")
    if clause_refs:
        response_parts.append(
            "\n*Referenced clauses: " + ", ".join(sorted(clause_refs)[:10]) + "*"
        )

    response_parts.append(
        "\n\n> **Note:** This response was generated in mock mode for testing. "
        "Switch to Anthropic Claude for production-quality analysis."
    )

    return "".join(response_parts)

"""LLM-powered extraction for freeform contract fields.

Uses Claude (anthropic mode) or keyword heuristics (mock mode) to extract
narrative fields like scope of work, security requirements, and special
provisions that are difficult to capture with regex alone.
"""

import json
import re


def extract_freeform_fields(text: str, mode: str = "mock", api_key: str | None = None) -> dict:
    """Extract freeform/narrative fields from contract text.

    Args:
        text: Full contract text content.
        mode: "mock" for keyword heuristics, "anthropic" for Claude API.
        api_key: Anthropic API key (required for anthropic mode).

    Returns:
        Dict with keys:
            - scope_of_work: str or None
            - security_requirements: list[str]
            - special_provisions: list[str]
            - domain: str or None (cybersecurity, it_modernization, etc.)
            - confidence: float (overall confidence)
    """
    if mode == "anthropic" and api_key:
        return _extract_with_llm(text, api_key)
    else:
        return _extract_with_keywords(text)


def _extract_with_llm(text: str, api_key: str) -> dict:
    """Use Claude to extract freeform fields."""
    try:
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            api_key=api_key,
            temperature=0,
            max_tokens=1500,
        )

        prompt = f"""You are a federal contract analyst. Extract these fields from the contract text below.
Return ONLY valid JSON with no markdown formatting, no explanation.

Fields to extract:
- scope_of_work: string (the complete statement of work / description of services). If not found, set to null.
- security_requirements: list of strings (clearance levels, CMMC, NIST requirements). Empty list if none found.
- special_provisions: list of strings (key personnel, EVMS, reporting requirements, GFE, etc.). Empty list if none found.
- domain: one of "cybersecurity", "it_modernization", "engineering", "consulting", or null if unclear.

CONTRACT TEXT:
{text[:8000]}

Return JSON:"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        # Clean up response — remove markdown code fences if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        result = json.loads(content)

        return {
            "scope_of_work": result.get("scope_of_work"),
            "security_requirements": result.get("security_requirements", []),
            "special_provisions": result.get("special_provisions", []),
            "domain": result.get("domain"),
            "confidence": 0.85,
        }

    except Exception as e:
        # Fall back to keyword extraction on any error
        fallback = _extract_with_keywords(text)
        fallback["llm_error"] = str(e)
        return fallback


def _extract_with_keywords(text: str) -> dict:
    """Keyword-based heuristic extraction for mock/fallback mode.

    Scans for recognizable phrases and extracts surrounding context.
    Returns with low confidence (0.3) so reports clearly flag these
    as approximate extractions.
    """
    scope = _extract_scope_keywords(text)
    security = _extract_security_keywords(text)
    provisions = _extract_provisions_keywords(text)
    domain = _detect_domain(text)

    return {
        "scope_of_work": scope,
        "security_requirements": security,
        "special_provisions": provisions,
        "domain": domain,
        "confidence": 0.3,
    }


def _extract_scope_keywords(text: str) -> str | None:
    """Extract scope of work using keyword/section detection."""
    # Look for explicit SOW section
    sow_patterns = [
        r"(?:STATEMENT OF WORK|SCOPE OF WORK|SOW|DESCRIPTION OF SERVICES)[:\s\-]*\n(.+?)(?:\n---|\n\n\n|\nCONTRACT LINE|\nAPPLICABLE)",
        r"(?:The contractor shall provide|Contractor shall perform)(.+?)(?:\.\s*\n\n|\.\s*---)",
    ]

    for pattern in sow_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            sow = match.group(1).strip()
            # Clean up and truncate if very long
            sow = re.sub(r"\s+", " ", sow)
            if len(sow) > 500:
                sow = sow[:500].rsplit(".", 1)[0] + "."
            if len(sow) > 20:
                return sow

    # Last resort: look for paragraphs with service-related keywords
    sentences = text.split(".")
    service_sentences = []
    keywords = ["shall provide", "shall perform", "services include",
                "scope of", "work includes", "deliverables"]
    for sentence in sentences:
        if any(kw in sentence.lower() for kw in keywords):
            clean = sentence.strip()
            if 20 < len(clean) < 500:
                service_sentences.append(clean + ".")
                if len(service_sentences) >= 3:
                    break

    if service_sentences:
        return " ".join(service_sentences)

    return None


def _extract_security_keywords(text: str) -> list[str]:
    """Extract security requirements using keyword matching."""
    requirements = []

    # Look for explicit security section
    sec_match = re.search(
        r"(?:SECURITY REQUIREMENTS|SECURITY CLASSIFICATION|CLEARANCE)[:\s\-]*\n(.+?)(?:\n---|\n\n\n)",
        text, re.IGNORECASE | re.DOTALL,
    )
    if sec_match:
        sec_text = sec_match.group(1)
        # Extract individual requirements (bullet points or lines)
        for line in sec_text.split("\n"):
            line = line.strip().lstrip("-").lstrip("*").strip()
            if len(line) > 10:
                requirements.append(line)

    # Keyword-based extraction
    security_patterns = [
        (r"(?:SECRET|TOP SECRET|TS/SCI)\s+(?:clearance|security)", "Security clearance required"),
        (r"CMMC\s+Level\s+(\d)", "CMMC Level {} certification required"),
        (r"NIST\s+SP\s+800[-]171", "NIST SP 800-171 compliance required"),
        (r"NIST\s+SP\s+800[-]53", "NIST SP 800-53 controls required"),
        (r"(?:FedRAMP|FISMA)\s+(?:authorization|compliance|moderate|high)", "FedRAMP/FISMA compliance required"),
        (r"DD[-\s]254", "DD-254 security classification specification required"),
        (r"ITAR\s+(?:compliance|controlled|restrictions)", "ITAR compliance required"),
    ]

    for pattern, template in security_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if "{}" in template:
                req = template.format(match.group(1))
            else:
                req = template
            if req not in requirements:
                requirements.append(req)

    return requirements


def _extract_provisions_keywords(text: str) -> list[str]:
    """Extract special provisions using keyword matching."""
    provisions = []

    # Look for explicit provisions section
    prov_match = re.search(
        r"(?:SPECIAL.*?PROVISIONS|SPECIAL.*?REQUIREMENTS|ADDITIONAL.*?TERMS)[:\s\-]*\n(.+?)(?:\n---|\n\n\n)",
        text, re.IGNORECASE | re.DOTALL,
    )
    if prov_match:
        prov_text = prov_match.group(1)
        for line in prov_text.split("\n"):
            line = line.strip().lstrip("-").lstrip("*").strip()
            if len(line) > 10:
                provisions.append(line)

    # Keyword-based patterns
    provision_patterns = [
        (r"Key\s+Personnel[:\s]+(.+?)(?:\n|$)", None),
        (r"(?:EVMS|Earned\s+Value\s+Management)", "Earned Value Management System (EVMS) reporting required"),
        (r"Government[-\s]Furnished\s+(?:Equipment|Property|Information)", "Government-furnished equipment/property provided"),
        (r"DevSecOps", "DevSecOps pipeline implementation required"),
        (r"(?:monthly|quarterly|weekly)\s+(?:status|progress)\s+report", "Periodic status reporting required"),
        (r"Organizational\s+Conflict\s+of\s+Interest", "Organizational Conflict of Interest mitigation plan required"),
        (r"(?:Transition|Phase[-\s]?In)\s+(?:plan|period)", "Transition/Phase-in plan required"),
    ]

    for pattern, default_text in provision_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if default_text:
                if default_text not in provisions:
                    provisions.append(default_text)
            else:
                extracted = match.group(1).strip() if match.lastindex else match.group(0).strip()
                if extracted not in provisions:
                    provisions.append(extracted)

    return provisions


def _detect_domain(text: str) -> str | None:
    """Detect the contract domain based on keyword frequency."""
    text_lower = text.lower()

    domain_keywords = {
        "cybersecurity": [
            "cybersecurity", "cyber security", "vulnerability", "penetration test",
            "incident response", "soc", "siem", "zero trust", "endpoint",
            "threat", "malware", "intrusion", "nist 800",
        ],
        "it_modernization": [
            "cloud migration", "modernization", "digital transformation",
            "legacy system", "microservices", "devops", "agile", "api gateway",
            "containerization", "kubernetes", "ci/cd",
        ],
        "engineering": [
            "systems engineering", "hardware", "firmware", "prototype",
            "manufacturing", "logistics", "sustainment", "test and evaluation",
            "integration testing", "mil-std",
        ],
        "consulting": [
            "advisory", "consulting", "strategic planning", "program management",
            "acquisition support", "training", "organizational assessment",
            "change management", "workforce",
        ],
    }

    scores = {}
    for domain, keywords in domain_keywords.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[domain] = score

    if scores:
        return max(scores, key=scores.get)
    return None

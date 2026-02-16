"""Synthetic federal contract generator.

Generates realistic federal contracts with proper FAR/DFARS clause references,
contract structures, and defense contracting terminology. All data is synthetic
and marked accordingly.

Usage:
    python -m src.data_generation.contract_generator --count 120 --output data/synthetic
"""

import json
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from faker import Faker

from .far_clauses import (
    FAR_CLAUSES,
    DFARS_CLAUSES,
    MANDATORY_FLOWDOWN_CLAUSES,
    NAICS_CODES,
    PSC_CODES,
)

fake = Faker()
Faker.seed(42)
random.seed(42)

# Contract vehicle types
CONTRACT_TYPES = ["FFP", "CPFF", "CPAF", "T&M", "LH", "IDIQ", "BPA"]
CONTRACT_TYPE_NAMES = {
    "FFP": "Firm-Fixed-Price",
    "CPFF": "Cost-Plus-Fixed-Fee",
    "CPAF": "Cost-Plus-Award-Fee",
    "T&M": "Time-and-Materials",
    "LH": "Labor-Hour",
    "IDIQ": "Indefinite Delivery/Indefinite Quantity",
    "BPA": "Blanket Purchase Agreement",
}

# Federal agencies
AGENCIES = [
    {"code": "DOD", "name": "Department of Defense", "prefix": "W911NF"},
    {"code": "ARMY", "name": "U.S. Army", "prefix": "W56KGZ"},
    {"code": "NAVY", "name": "U.S. Navy", "prefix": "N00024"},
    {"code": "USAF", "name": "U.S. Air Force", "prefix": "FA8650"},
    {"code": "DHS", "name": "Department of Homeland Security", "prefix": "70CDCR"},
    {"code": "VA", "name": "Department of Veterans Affairs", "prefix": "36C10X"},
    {"code": "DOE", "name": "Department of Energy", "prefix": "DE-AC05"},
    {"code": "NASA", "name": "National Aeronautics and Space Administration", "prefix": "NNJ14"},
    {"code": "DISA", "name": "Defense Information Systems Agency", "prefix": "HC1028"},
    {"code": "DLA", "name": "Defense Logistics Agency", "prefix": "SP4701"},
]

# Synthetic company names for the contractor ecosystem
PRIME_CONTRACTORS = [
    {"name": "Meridian Defense Technologies", "cage": "5K4M7", "size": "large"},
    {"name": "Atlas Federal Solutions", "cage": "3R8N2", "size": "large"},
    {"name": "Vanguard Systems International", "cage": "7P2L9", "size": "large"},
    {"name": "Pinnacle Cyber Defense Corp", "cage": "1X6T4", "size": "mid"},
    {"name": "Horizon IT Federal", "cage": "9D3F8", "size": "mid"},
    {"name": "Sentinel Mission Systems", "cage": "4W7K1", "size": "mid"},
    {"name": "ClearPath Analytics Group", "cage": "2H5G6", "size": "small"},
    {"name": "RedOak Consulting LLC", "cage": "8B9Q3", "size": "small"},
    {"name": "TrueNorth Federal Services", "cage": "6Y1R5", "size": "small"},
    {"name": "Apex Integration Partners", "cage": "0M4J7", "size": "small"},
]

SUBCONTRACTORS = [
    {"name": "DataForge Analytics Inc", "cage": "3F7P2", "size": "small"},
    {"name": "SecureNet Consulting LLC", "cage": "8K1M5", "size": "small"},
    {"name": "CloudBridge Federal", "cage": "2T9R4", "size": "small"},
    {"name": "CyberShield Solutions", "cage": "5N3D8", "size": "small"},
    {"name": "Quantum Leap Technologies", "cage": "7G6L1", "size": "8a"},
    {"name": "IronClad Systems Inc", "cage": "1P8W3", "size": "sdvosb"},
    {"name": "BrightPath IT Services", "cage": "4J2X6", "size": "wosb"},
    {"name": "Heritage Defense Group", "cage": "9A5K7", "size": "hubzone"},
]

# IDIQ vehicle names
IDIQ_VEHICLES = [
    "OASIS+ Unrestricted",
    "OASIS+ Small Business",
    "Alliant 2",
    "CIO-SP4",
    "SEWP V",
    "ITES-3S",
    "EAGLE II",
    "VETS 2",
    "GSA MAS IT Category",
    "STARS III",
]

# Scope of work descriptions by domain
SOW_TEMPLATES = {
    "cybersecurity": [
        "Cybersecurity Assessment and Authorization (A&A) services for {agency} enterprise systems, including Risk Management Framework (RMF) implementation, continuous monitoring, and vulnerability management across classified and unclassified environments.",
        "Security Operations Center (SOC) staffing and management, including 24/7 monitoring, incident response, threat intelligence analysis, and forensic investigation capabilities for {agency} networks.",
        "CMMC assessment preparation and remediation services, including gap analysis against NIST SP 800-171 controls, Plan of Action and Milestones (POA&M) development, and security control implementation.",
        "Zero Trust Architecture design and implementation for {agency}, including identity management, micro-segmentation, software-defined perimeter deployment, and continuous verification protocols.",
    ],
    "it_modernization": [
        "Legacy system modernization and cloud migration for {agency} enterprise applications, including assessment of current infrastructure, development of migration roadmaps, and implementation of cloud-native architectures on AWS GovCloud or Azure Government.",
        "Enterprise Resource Planning (ERP) implementation and integration services, including Deltek Costpoint configuration, data migration from legacy systems, and custom module development for {agency} requirements.",
        "Application development and sustainment services for mission-critical {agency} systems, including Agile/DevSecOps implementation, CI/CD pipeline configuration, and automated testing frameworks.",
        "Digital transformation consulting services for {agency}, including business process reengineering, robotic process automation (RPA) implementation, and AI/ML capability development.",
    ],
    "engineering": [
        "Systems engineering and technical assistance (SETA) for {agency} acquisition programs, including requirements analysis, technical evaluation, test and evaluation planning, and program management support.",
        "Research, development, test, and evaluation (RDT&E) support for {agency} sensor systems, including prototype development, performance testing, and technology readiness assessment.",
        "Logistics engineering and sustainment support for {agency} weapon systems, including reliability analysis, maintainability assessment, and supply chain optimization.",
    ],
    "consulting": [
        "Strategic management consulting services for {agency} organizational transformation, including operating model design, change management, and performance measurement framework development.",
        "Financial management and audit readiness services for {agency}, including internal controls assessment, financial statement preparation support, and FIAR compliance assistance.",
        "Human capital management services for {agency}, including workforce planning, competency modeling, training program development, and organizational assessment.",
    ],
}

# Contract Line Item (CLIN) descriptions
CLIN_DESCRIPTIONS = {
    "labor": [
        "Program Management Support",
        "Senior Systems Engineer",
        "Cybersecurity Analyst Level III",
        "Software Developer (Full Stack)",
        "Data Analyst/Scientist",
        "Cloud Architecture Engineer",
        "Network Security Engineer",
        "Help Desk Support Specialist",
        "Quality Assurance Analyst",
        "Technical Writer",
        "Business Analyst",
        "Database Administrator",
        "DevSecOps Engineer",
        "Information Assurance Engineer",
        "Project Coordinator",
    ],
    "materials": [
        "Hardware and Software Licenses",
        "Cloud Infrastructure Services (IaaS/PaaS)",
        "Security Tooling and Licenses",
        "Travel and Other Direct Costs (ODCs)",
        "Training Materials and Certifications",
    ],
    "deliverables": [
        "System Security Plan (SSP) Documentation",
        "Monthly Status Reports",
        "Quarterly Program Reviews",
        "Technical Architecture Document",
        "Migration Roadmap and Implementation Plan",
        "Risk Assessment Report",
        "Incident Response Plan",
        "Continuity of Operations Plan (COOP)",
        "After Action Report",
        "Lessons Learned Documentation",
    ],
}


def generate_contract_number(agency: dict, year: int) -> str:
    """Generate a realistic federal contract number."""
    suffix = f"{random.randint(0, 9999):04d}"
    contract_type = random.choice(["C", "D", "F"])
    return f"{agency['prefix']}-{year % 100:02d}-{contract_type}-{suffix}"


def generate_task_order_number(base_contract: str) -> str:
    """Generate a task order number under an IDIQ contract."""
    to_num = random.randint(1, 99)
    return f"{base_contract}-TO-{to_num:04d}"


def select_clauses(contract_type: str, value: float, is_dod: bool) -> dict:
    """Select appropriate FAR/DFARS clauses based on contract characteristics."""
    selected_far = []
    selected_dfars = []

    # Always include general clauses
    selected_far.extend(FAR_CLAUSES["general"])

    # Always include labor clauses for service contracts
    selected_far.extend(random.sample(FAR_CLAUSES["labor"], min(4, len(FAR_CLAUSES["labor"]))))

    # Always include payment clauses
    selected_far.extend(FAR_CLAUSES["payment"])

    # Include termination clauses
    selected_far.extend(random.sample(FAR_CLAUSES["termination"], min(2, len(FAR_CLAUSES["termination"]))))

    # Include IP clauses
    selected_far.extend(FAR_CLAUSES["intellectual_property"])

    # Subcontracting clauses for larger contracts
    if value > 750_000:
        selected_far.extend(FAR_CLAUSES["subcontracting"])

    # Competition clauses
    selected_far.extend(FAR_CLAUSES["competition"])

    # Inspection
    selected_far.extend(FAR_CLAUSES["inspection"])

    # Changes
    selected_far.extend(FAR_CLAUSES["changes"])

    # Cybersecurity (FAR)
    selected_far.extend(FAR_CLAUSES["cybersecurity"])

    # DoD-specific DFARS clauses
    if is_dod:
        selected_dfars.extend(DFARS_CLAUSES["cybersecurity"])
        selected_dfars.extend(DFARS_CLAUSES["security"])
        selected_dfars.extend(random.sample(
            DFARS_CLAUSES["supply_chain"],
            min(2, len(DFARS_CLAUSES["supply_chain"]))
        ))
        selected_dfars.extend(DFARS_CLAUSES["intellectual_property"])

        if value > 2_000_000:
            selected_dfars.extend(DFARS_CLAUSES["cost_accounting"])
            selected_dfars.extend(DFARS_CLAUSES["subcontracting"])

        if random.random() > 0.5:
            selected_dfars.extend(DFARS_CLAUSES["export_control"])

    return {"far": selected_far, "dfars": selected_dfars}


def generate_clins(contract_type: str, value: float) -> list[dict]:
    """Generate Contract Line Items (CLINs)."""
    clins = []
    num_clins = random.randint(3, 8)
    remaining_value = value

    # Labor CLINs
    labor_items = random.sample(CLIN_DESCRIPTIONS["labor"], min(num_clins - 1, len(CLIN_DESCRIPTIONS["labor"])))
    for i, desc in enumerate(labor_items):
        clin_value = remaining_value * random.uniform(0.1, 0.4) if i < len(labor_items) - 1 else remaining_value * 0.5
        clin_value = round(clin_value, 2)
        remaining_value -= clin_value

        clins.append({
            "clin_number": f"{i + 1:04d}",
            "description": desc,
            "type": "Labor" if contract_type in ["T&M", "LH"] else "FFP",
            "quantity": random.randint(1, 12) if contract_type in ["T&M", "LH"] else 1,
            "unit": "Hours" if contract_type in ["T&M", "LH"] else "Lot",
            "unit_price": round(random.uniform(85, 285), 2) if contract_type in ["T&M", "LH"] else round(clin_value, 2),
            "total_price": round(clin_value, 2),
        })

    # Materials/ODC CLIN
    mat_desc = random.choice(CLIN_DESCRIPTIONS["materials"])
    mat_value = round(remaining_value * random.uniform(0.3, 0.7), 2)
    clins.append({
        "clin_number": f"{len(clins) + 1:04d}",
        "description": mat_desc,
        "type": "Cost-Reimbursable",
        "quantity": 1,
        "unit": "Lot",
        "unit_price": mat_value,
        "total_price": mat_value,
    })

    # Deliverables CLIN (if applicable)
    if random.random() > 0.3:
        del_desc = random.choice(CLIN_DESCRIPTIONS["deliverables"])
        clins.append({
            "clin_number": f"{len(clins) + 1:04d}",
            "description": del_desc,
            "type": "FFP",
            "quantity": random.randint(1, 12),
            "unit": "Each",
            "unit_price": 0.00,
            "total_price": 0.00,  # NSP - No Separate Price
        })

    return clins


def generate_period_of_performance() -> dict:
    """Generate period of performance dates."""
    start_year = random.randint(2021, 2025)
    start_month = random.randint(1, 12)
    start_date = datetime(start_year, start_month, 1)

    base_months = random.choice([6, 12, 18, 24, 36, 60])
    end_date = start_date + timedelta(days=base_months * 30)

    # Option periods
    num_options = random.randint(0, 4)
    options = []
    option_start = end_date + timedelta(days=1)
    for i in range(num_options):
        option_months = random.choice([6, 12])
        option_end = option_start + timedelta(days=option_months * 30)
        options.append({
            "option_number": i + 1,
            "start_date": option_start.strftime("%Y-%m-%d"),
            "end_date": option_end.strftime("%Y-%m-%d"),
            "months": option_months,
        })
        option_start = option_end + timedelta(days=1)

    return {
        "base_period_start": start_date.strftime("%Y-%m-%d"),
        "base_period_end": end_date.strftime("%Y-%m-%d"),
        "base_period_months": base_months,
        "option_periods": options,
    }


def generate_subcontractor_requirements(value: float) -> list[dict]:
    """Generate subcontractor provisions and flowdown requirements."""
    if value < 750_000:
        return []

    num_subs = random.randint(1, 4)
    subs = random.sample(SUBCONTRACTORS, min(num_subs, len(SUBCONTRACTORS)))

    sub_requirements = []
    for sub in subs:
        sub_value = value * random.uniform(0.05, 0.25)
        sub_requirements.append({
            "subcontractor_name": sub["name"],
            "cage_code": sub["cage"],
            "business_size": sub["size"],
            "estimated_value": round(sub_value, 2),
            "scope": random.choice([
                "Cybersecurity assessment and monitoring support",
                "Software development and integration services",
                "Cloud infrastructure management",
                "Data analytics and reporting",
                "Help desk and end-user support",
                "Training and certification services",
                "Network engineering support",
                "Quality assurance testing",
            ]),
            "flowdown_clauses": [c for c in MANDATORY_FLOWDOWN_CLAUSES if random.random() > 0.3],
        })

    return sub_requirements


def contract_to_document(contract: dict) -> str:
    """Convert structured contract data to a text document for RAG ingestion."""
    lines = []
    lines.append("=" * 80)
    lines.append("*** SYNTHETIC DATA - FOR PORTFOLIO DEMONSTRATION ONLY ***")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"CONTRACT NUMBER: {contract['contract_number']}")
    if contract.get("parent_idiq"):
        lines.append(f"PARENT IDIQ CONTRACT: {contract['parent_idiq']}")
    lines.append(f"CONTRACT TYPE: {contract['contract_type_name']} ({contract['contract_type']})")
    lines.append(f"CONTRACTING AGENCY: {contract['agency']['name']} ({contract['agency']['code']})")
    lines.append(f"CONTRACTING OFFICER: {contract['contracting_officer']}")
    lines.append("")

    lines.append("--- CONTRACTOR INFORMATION ---")
    lines.append(f"Contractor: {contract['contractor']['name']}")
    lines.append(f"CAGE Code: {contract['contractor']['cage']}")
    lines.append(f"Business Size: {contract['contractor']['size']}")
    lines.append(f"DUNS/UEI: {contract['contractor']['uei']}")
    lines.append("")

    if contract.get("idiq_vehicle"):
        lines.append(f"CONTRACT VEHICLE: {contract['idiq_vehicle']}")
        lines.append("")

    lines.append(f"NAICS CODE: {contract['naics_code']} - {NAICS_CODES[contract['naics_code']]}")
    lines.append(f"PSC CODE: {contract['psc_code']} - {PSC_CODES[contract['psc_code']]}")
    lines.append("")

    lines.append("--- TOTAL CONTRACT VALUE ---")
    lines.append(f"Base Period Value: ${contract['value']:,.2f}")
    if contract.get("ceiling_value"):
        lines.append(f"Contract Ceiling: ${contract['ceiling_value']:,.2f}")
    lines.append(f"Funded Amount: ${contract['funded_amount']:,.2f}")
    lines.append("")

    lines.append("--- PERIOD OF PERFORMANCE ---")
    pop = contract["period_of_performance"]
    lines.append(f"Base Period: {pop['base_period_start']} through {pop['base_period_end']} ({pop['base_period_months']} months)")
    for opt in pop.get("option_periods", []):
        lines.append(f"Option Period {opt['option_number']}: {opt['start_date']} through {opt['end_date']} ({opt['months']} months)")
    lines.append("")

    lines.append("--- STATEMENT OF WORK ---")
    lines.append(contract["scope_of_work"])
    lines.append("")

    lines.append("--- CONTRACT LINE ITEMS (CLINs) ---")
    for clin in contract["clins"]:
        lines.append(f"  CLIN {clin['clin_number']}: {clin['description']}")
        lines.append(f"    Type: {clin['type']} | Qty: {clin['quantity']} {clin['unit']} | Unit Price: ${clin['unit_price']:,.2f} | Total: ${clin['total_price']:,.2f}")
    lines.append("")

    lines.append("--- APPLICABLE FAR CLAUSES ---")
    for clause in contract["clauses"]["far"]:
        lines.append(f"  FAR {clause['number']} - {clause['title']}")
        lines.append(f"    {clause['text']}")
        lines.append("")

    lines.append("--- APPLICABLE DFARS CLAUSES ---")
    if contract["clauses"]["dfars"]:
        for clause in contract["clauses"]["dfars"]:
            flowdown_marker = " [MANDATORY FLOWDOWN]" if clause.get("flowdown") else ""
            lines.append(f"  DFARS {clause['number']} - {clause['title']}{flowdown_marker}")
            lines.append(f"    {clause['text']}")
            lines.append("")
    else:
        lines.append("  No DFARS clauses applicable (non-DoD contract).")
        lines.append("")

    if contract.get("subcontractor_requirements"):
        lines.append("--- SUBCONTRACTOR REQUIREMENTS ---")
        for sub in contract["subcontractor_requirements"]:
            lines.append(f"  Subcontractor: {sub['subcontractor_name']} (CAGE: {sub['cage_code']})")
            lines.append(f"    Business Size: {sub['business_size']}")
            lines.append(f"    Estimated Value: ${sub['estimated_value']:,.2f}")
            lines.append(f"    Scope: {sub['scope']}")
            if sub.get("flowdown_clauses"):
                lines.append(f"    Flowdown Clauses: {', '.join(sub['flowdown_clauses'])}")
            lines.append("")

    if contract.get("security_requirements"):
        lines.append("--- SECURITY REQUIREMENTS ---")
        for req in contract["security_requirements"]:
            lines.append(f"  - {req}")
        lines.append("")

    if contract.get("special_provisions"):
        lines.append("--- SPECIAL CONTRACT PROVISIONS ---")
        for provision in contract["special_provisions"]:
            lines.append(f"  {provision}")
        lines.append("")

    lines.append("--- END OF CONTRACT ---")
    lines.append("*** SYNTHETIC DATA - FOR PORTFOLIO DEMONSTRATION ONLY ***")

    return "\n".join(lines)


def generate_single_contract(
    contract_id: int,
    parent_idiq: str | None = None,
    force_type: str | None = None,
) -> dict:
    """Generate a single synthetic contract."""
    agency = random.choice(AGENCIES)
    is_dod = agency["code"] in ["DOD", "ARMY", "NAVY", "USAF", "DISA", "DLA"]

    if force_type:
        contract_type = force_type
    elif parent_idiq:
        contract_type = random.choice(["FFP", "CPFF", "T&M", "LH"])
    else:
        weights = [30, 20, 10, 15, 10, 10, 5]
        contract_type = random.choices(CONTRACT_TYPES, weights=weights, k=1)[0]

    contractor = random.choice(PRIME_CONTRACTORS)

    # Contract value based on type
    if contract_type == "IDIQ":
        value = round(random.uniform(5_000_000, 500_000_000), 2)
        ceiling_value = round(value * random.uniform(1.5, 5.0), 2)
        funded_amount = round(value * random.uniform(0.1, 0.3), 2)
    elif contract_type == "BPA":
        value = round(random.uniform(100_000, 5_000_000), 2)
        ceiling_value = round(value * 2, 2)
        funded_amount = round(value * random.uniform(0.2, 0.5), 2)
    else:
        value = round(random.uniform(150_000, 25_000_000), 2)
        ceiling_value = None
        funded_amount = round(value * random.uniform(0.5, 1.0), 2)

    year = random.randint(2021, 2025)

    if parent_idiq:
        contract_number = generate_task_order_number(parent_idiq)
    else:
        contract_number = generate_contract_number(agency, year)

    # Select domain and SOW
    domain = random.choice(list(SOW_TEMPLATES.keys()))
    sow_template = random.choice(SOW_TEMPLATES[domain])
    scope_of_work = sow_template.format(agency=agency["name"])

    # Security requirements
    security_reqs = []
    if is_dod:
        security_reqs.append("Contractor personnel must hold active SECRET clearance or higher")
        if random.random() > 0.5:
            security_reqs.append("Facility must have TOP SECRET Facility Clearance (FCL)")
        security_reqs.append("CMMC Level 2 certification required prior to contract award")
        if domain == "cybersecurity":
            security_reqs.append("Compliance with NIST SP 800-171 Rev 2 required for all covered systems")
            security_reqs.append("Cyber incident reporting within 72 hours per DFARS 252.204-7012")

    # Special provisions
    special_provisions = []
    if value > 10_000_000:
        special_provisions.append("Earned Value Management System (EVMS) reporting required per DID DI-MGMT-81861A")
    if domain in ["cybersecurity", "it_modernization"]:
        special_provisions.append("Contractor shall implement a DevSecOps pipeline in accordance with DoD Enterprise DevSecOps Reference Design")
    if random.random() > 0.6:
        special_provisions.append(f"Key Personnel: Program Manager, {random.choice(['Chief Engineer', 'Technical Lead', 'Security Lead'])} - substitution requires 30-day advance written notice and CO approval")
    if random.random() > 0.7:
        special_provisions.append("Government Furnished Equipment (GFE) will be provided; Contractor is responsible for GFE accountability per FAR 52.245-1")

    naics = random.choice(list(NAICS_CODES.keys()))
    psc = random.choice(list(PSC_CODES.keys()))

    contract = {
        "id": contract_id,
        "contract_number": contract_number,
        "parent_idiq": parent_idiq,
        "contract_type": contract_type,
        "contract_type_name": CONTRACT_TYPE_NAMES[contract_type],
        "agency": {"code": agency["code"], "name": agency["name"]},
        "contracting_officer": fake.name(),
        "contractor": {
            "name": contractor["name"],
            "cage": contractor["cage"],
            "size": contractor["size"],
            "uei": fake.bothify("??########").upper(),
        },
        "idiq_vehicle": random.choice(IDIQ_VEHICLES) if contract_type == "IDIQ" else None,
        "naics_code": naics,
        "psc_code": psc,
        "value": value,
        "ceiling_value": ceiling_value,
        "funded_amount": funded_amount,
        "period_of_performance": generate_period_of_performance(),
        "scope_of_work": scope_of_work,
        "domain": domain,
        "clins": generate_clins(contract_type, value),
        "clauses": select_clauses(contract_type, value, is_dod),
        "subcontractor_requirements": generate_subcontractor_requirements(value),
        "security_requirements": security_reqs,
        "special_provisions": special_provisions,
        "is_dod": is_dod,
        "synthetic": True,
    }

    # Generate text document representation
    contract["document_text"] = contract_to_document(contract)

    return contract


def generate_contracts(count: int = 120) -> list[dict]:
    """Generate a full corpus of synthetic contracts."""
    contracts = []
    contract_id = 1

    # Distribution:
    # 35 FFP, 20 CPFF, 10 CPAF, 15 T&M, 10 LH, 15 IDIQ base, 10 BPA, 5 task orders
    type_distribution = {
        "FFP": 35,
        "CPFF": 20,
        "CPAF": 10,
        "T&M": 15,
        "LH": 10,
        "IDIQ": 15,
        "BPA": 10,
    }

    # Generate base contracts
    idiq_contracts = []
    for ctype, num in type_distribution.items():
        for _ in range(min(num, count - len(contracts))):
            if len(contracts) >= count:
                break
            contract = generate_single_contract(contract_id, force_type=ctype)
            contracts.append(contract)
            if ctype == "IDIQ":
                idiq_contracts.append(contract)
            contract_id += 1

    # Generate task orders under IDIQ contracts
    remaining = count - len(contracts)
    for _ in range(remaining):
        parent = random.choice(idiq_contracts)
        to = generate_single_contract(
            contract_id,
            parent_idiq=parent["contract_number"],
        )
        contracts.append(to)
        contract_id += 1

    random.shuffle(contracts)
    return contracts


def save_contracts(contracts: list[dict], output_dir: str | Path) -> None:
    """Save generated contracts to individual JSON files and a corpus file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save individual contract JSON files
    for contract in contracts:
        filename = contract["contract_number"].replace("/", "_").replace(" ", "_")
        filepath = output_path / f"{filename}.json"
        with open(filepath, "w") as f:
            json.dump(contract, f, indent=2, default=str)

    # Save full corpus as a single file for easy loading
    corpus_path = output_path / "_corpus.json"
    with open(corpus_path, "w") as f:
        json.dump(contracts, f, indent=2, default=str)

    # Save text documents for RAG ingestion
    docs_path = output_path / "documents"
    docs_path.mkdir(exist_ok=True)
    for contract in contracts:
        filename = contract["contract_number"].replace("/", "_").replace(" ", "_")
        filepath = docs_path / f"{filename}.txt"
        with open(filepath, "w") as f:
            f.write(contract["document_text"])

    print(f"Generated {len(contracts)} synthetic contracts")
    print(f"  JSON files: {output_path}")
    print(f"  Text documents: {docs_path}")
    print(f"  Corpus file: {corpus_path}")

    # Print statistics
    type_counts: dict[str, int] = {}
    for c in contracts:
        t = c["contract_type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    print("\nContract type distribution:")
    for t, n in sorted(type_counts.items()):
        print(f"  {t}: {n}")

    agency_counts: dict[str, int] = {}
    for c in contracts:
        a = c["agency"]["code"]
        agency_counts[a] = agency_counts.get(a, 0) + 1
    print("\nAgency distribution:")
    for a, n in sorted(agency_counts.items(), key=lambda x: -x[1]):
        print(f"  {a}: {n}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic federal contracts")
    parser.add_argument("--count", type=int, default=120, help="Number of contracts to generate")
    parser.add_argument("--output", type=str, default="data/synthetic", help="Output directory")
    args = parser.parse_args()

    contracts = generate_contracts(args.count)
    save_contracts(contracts, args.output)


if __name__ == "__main__":
    main()

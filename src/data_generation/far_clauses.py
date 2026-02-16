"""FAR and DFARS clause reference data for synthetic contract generation.

Contains realistic clause numbers, titles, and descriptions used in federal contracts.
All content is synthetic but modeled on real FAR/DFARS structure.
"""

# Common FAR Part 52 clauses organized by category
FAR_CLAUSES = {
    "general": [
        {
            "number": "52.202-1",
            "title": "Definitions",
            "text": "When a solicitation provision or contract clause uses a word or term that is defined in the Federal Acquisition Regulation (FAR), the word or term has the same meaning as the definition in FAR. Terms defined in this clause apply throughout the contract.",
            "prescription": "FAR 2.201",
        },
        {
            "number": "52.203-3",
            "title": "Gratuities",
            "text": "The right of the Contractor to proceed may be terminated by written notice if, after notice and hearing, the agency head determines that the Contractor, its agent, or another representative offered or gave a gratuity to an officer, official, or employee of the Government.",
            "prescription": "FAR 3.202",
        },
        {
            "number": "52.203-13",
            "title": "Contractor Code of Business Ethics and Conduct",
            "text": "The Contractor shall have a written code of business ethics and conduct, and shall make a copy available to each employee engaged in performance of the contract. The Contractor shall exercise due diligence to prevent and detect criminal conduct.",
            "prescription": "FAR 3.1004(a)",
        },
        {
            "number": "52.204-13",
            "title": "System for Award Management Maintenance",
            "text": "The Contractor shall update the information in the SAM database on an annual basis from the date of initial registration or subsequent updates to the information, throughout the life of the contract.",
            "prescription": "FAR 4.1105(b)",
        },
    ],
    "competition": [
        {
            "number": "52.209-6",
            "title": "Protecting the Government's Interest When Subcontracting with Contractors Debarred, Suspended, or Proposed for Debarment",
            "text": "The Contractor shall not enter into any subcontract in excess of $35,000 with a contractor that is debarred, suspended, or proposed for debarment unless there is a compelling reason to do so.",
            "prescription": "FAR 9.409",
        },
        {
            "number": "52.209-10",
            "title": "Prohibition on Contracting with Inverted Domestic Corporations",
            "text": "The Contractor shall not use any funds received under this contract to enter into a subcontract with an entity that is an inverted domestic corporation or subsidiary of such corporation.",
            "prescription": "FAR 9.108-5",
        },
    ],
    "labor": [
        {
            "number": "52.222-1",
            "title": "Notice to the Government of Labor Disputes",
            "text": "If the Contractor has knowledge that any actual or potential labor dispute is delaying or threatens to delay the timely performance of this contract, the Contractor shall immediately give notice to the Contracting Officer.",
            "prescription": "FAR 22.103-5(a)",
        },
        {
            "number": "52.222-3",
            "title": "Convict Labor",
            "text": "The Contractor shall not employ in the performance of this contract any person undergoing a sentence of imprisonment imposed by any court of a State, the District of Columbia, Puerto Rico, or any territory or possession of the United States.",
            "prescription": "FAR 22.202",
        },
        {
            "number": "52.222-21",
            "title": "Prohibition of Segregated Facilities",
            "text": "The Contractor agrees that a breach of this clause is a violation of the Equal Opportunity clause in this contract. Segregated facilities means any waiting rooms, work areas, rest rooms, or other facilities that are segregated by explicit directive or are in fact segregated.",
            "prescription": "FAR 22.810(a)(1)",
        },
        {
            "number": "52.222-26",
            "title": "Equal Opportunity",
            "text": "During the performance of this contract, the Contractor agrees not to discriminate against any employee or applicant for employment because of race, color, religion, sex, sexual orientation, gender identity, or national origin.",
            "prescription": "FAR 22.810(e)",
        },
        {
            "number": "52.222-35",
            "title": "Equal Opportunity for Veterans",
            "text": "The Contractor shall not discriminate against any employee or applicant for employment because the individual is a disabled veteran, recently separated veteran, active duty wartime or campaign badge veteran, or Armed Forces service medal veteran.",
            "prescription": "FAR 22.1310(a)(1)",
        },
        {
            "number": "52.222-36",
            "title": "Equal Opportunity for Workers with Disabilities",
            "text": "The Contractor shall not discriminate against any employee or applicant for employment because of physical or mental disability in regard to any position for which the employee or applicant is qualified.",
            "prescription": "FAR 22.1408(a)",
        },
        {
            "number": "52.222-50",
            "title": "Combating Trafficking in Persons",
            "text": "The United States Government has a policy prohibiting trafficking in persons including the trafficking-related activities. The Contractor and subcontractors shall not engage in severe forms of trafficking, procure commercial sex acts, or use forced labor.",
            "prescription": "FAR 22.1705(a)(1)",
        },
    ],
    "intellectual_property": [
        {
            "number": "52.227-1",
            "title": "Authorization and Consent",
            "text": "The Government authorizes and consents to all use and manufacture, in performing this contract or any subcontract at any tier, of any invention described in and covered by a United States patent.",
            "prescription": "FAR 27.201-2(a)(1)",
        },
        {
            "number": "52.227-14",
            "title": "Rights in Data - General",
            "text": "The Government shall have unlimited rights in data first produced in the performance of this contract. The Contractor shall have the right to assert copyright in data first produced in performance of this contract.",
            "prescription": "FAR 27.409(b)(1)",
        },
    ],
    "payment": [
        {
            "number": "52.232-1",
            "title": "Payments",
            "text": "The Government shall pay the Contractor upon the submission of proper invoices or vouchers, the prices stipulated in this contract for supplies delivered and accepted or services rendered and accepted, less any deductions provided in this contract.",
            "prescription": "FAR 32.111(a)(1)",
        },
        {
            "number": "52.232-25",
            "title": "Prompt Payment",
            "text": "Notwithstanding any other payment clause in this contract, the Government will make invoice payments and contract financing payments in accordance with the Prompt Payment Act and the applicable regulations.",
            "prescription": "FAR 32.908(c)",
        },
        {
            "number": "52.232-33",
            "title": "Payment by Electronic Funds Transfer - System for Award Management",
            "text": "Method of payment. All payments by the Government under this contract shall be made by electronic funds transfer (EFT). The Contractor shall designate a financial institution for receipt of EFT payments.",
            "prescription": "FAR 32.1110(a)(1)",
        },
    ],
    "termination": [
        {
            "number": "52.249-1",
            "title": "Termination for Convenience of the Government (Fixed-Price) (Short Form)",
            "text": "The Contracting Officer, by written notice, may terminate this contract, in whole or in part, when it is in the Government's interest. If this contract is terminated, the Government shall be liable only for payment in accordance with the terms of this contract.",
            "prescription": "FAR 49.502(a)(1)",
        },
        {
            "number": "52.249-2",
            "title": "Termination for Convenience of the Government (Fixed-Price)",
            "text": "The Government may terminate performance of work under this contract in whole or, from time to time, in part if the Contracting Officer determines that a termination is in the Government's interest.",
            "prescription": "FAR 49.502(b)(1)(i)",
        },
        {
            "number": "52.249-8",
            "title": "Default (Fixed-Price Supply and Service)",
            "text": "If the Contractor fails to deliver the supplies or to perform the services within the time specified in this contract, the Government may terminate this contract for default.",
            "prescription": "FAR 49.504(a)(1)",
        },
    ],
    "changes": [
        {
            "number": "52.243-1",
            "title": "Changes - Fixed-Price",
            "text": "The Contracting Officer may at any time, by written order, make changes within the general scope of this contract in drawings, designs, or specifications; method of shipment or packing; or place of delivery.",
            "prescription": "FAR 43.205(a)(1)",
        },
    ],
    "inspection": [
        {
            "number": "52.246-2",
            "title": "Inspection of Supplies - Fixed-Price",
            "text": "The Contractor shall provide and maintain an inspection system acceptable to the Government covering the supplies under this contract. The Government has the right to inspect and test all supplies called for by the contract.",
            "prescription": "FAR 46.302",
        },
    ],
    "cybersecurity": [
        {
            "number": "52.204-21",
            "title": "Basic Safeguarding of Covered Contractor Information Systems",
            "text": "The Contractor shall apply the following basic safeguarding requirements and procedures to protect covered contractor information systems. At a minimum, the Contractor shall apply NIST SP 800-171 controls.",
            "prescription": "FAR 4.1903",
        },
    ],
    "subcontracting": [
        {
            "number": "52.219-8",
            "title": "Utilization of Small Business Concerns",
            "text": "It is the policy of the United States that small business concerns shall have the maximum practicable opportunity to participate in performing contracts let by any Federal agency.",
            "prescription": "FAR 19.708(a)",
        },
        {
            "number": "52.219-9",
            "title": "Small Business Subcontracting Plan",
            "text": "The Contractor shall adopt a subcontracting plan that separately addresses subcontracting with small business concerns, including goals for each category of small business.",
            "prescription": "FAR 19.708(b)(1)",
        },
        {
            "number": "52.244-2",
            "title": "Subcontracts",
            "text": "The Contractor shall notify the Contracting Officer reasonably in advance of placing any subcontract if the subcontract is for a critical component or involves specific types defined in this clause.",
            "prescription": "FAR 44.204(a)",
        },
        {
            "number": "52.244-6",
            "title": "Subcontracts for Commercial Products and Commercial Services",
            "text": "To the maximum extent practicable, the Contractor shall incorporate commercial products or commercial services as components of items delivered under this contract.",
            "prescription": "FAR 44.403",
        },
    ],
}

# DFARS clauses (Defense-specific)
DFARS_CLAUSES = {
    "cybersecurity": [
        {
            "number": "252.204-7008",
            "title": "Compliance with Safeguarding Covered Defense Information Controls",
            "text": "The Offeror represents that it will implement the security requirements specified by NIST SP 800-171 not later than December 31, 2017. Covered defense information shall be safeguarded in accordance with these requirements.",
            "prescription": "DFARS 204.7304(a)",
        },
        {
            "number": "252.204-7012",
            "title": "Safeguarding Covered Defense Information and Cyber Incident Reporting",
            "text": "The Contractor shall implement NIST SP 800-171 to provide adequate security on all covered contractor information systems. The Contractor shall rapidly report cyber incidents directly to DoD at https://dibnet.dod.mil within 72 hours of discovery.",
            "prescription": "DFARS 204.7304(c)",
            "flowdown": True,
        },
        {
            "number": "252.204-7019",
            "title": "Notice of NIST SP 800-171 DoD Assessment Requirements",
            "text": "The Offeror shall have a current assessment of the NIST SP 800-171 security requirements conducted in accordance with the NIST SP 800-171 DoD Assessment Methodology.",
            "prescription": "DFARS 204.7304(d)",
        },
        {
            "number": "252.204-7020",
            "title": "NIST SP 800-171 DoD Assessment Requirements",
            "text": "The Contractor shall provide access to its facilities, systems, and personnel when it is necessary for DoD to conduct or renew a higher-level assessment of the Contractor's compliance with NIST SP 800-171.",
            "prescription": "DFARS 204.7304(e)",
        },
        {
            "number": "252.204-7021",
            "title": "Cybersecurity Maturity Model Certification Requirements",
            "text": "The Contractor shall have a current CMMC certificate at the CMMC level specified in the solicitation at time of award and maintain the CMMC certificate at the required level for the duration of the contract.",
            "prescription": "DFARS 204.7503",
            "flowdown": True,
        },
    ],
    "export_control": [
        {
            "number": "252.225-7048",
            "title": "Export-Controlled Items",
            "text": "The Contractor shall comply with all applicable laws and regulations regarding export-controlled items, including the International Traffic in Arms Regulations (ITAR) and the Export Administration Regulations (EAR).",
            "prescription": "DFARS 225.7901-4",
            "flowdown": True,
        },
    ],
    "cost_accounting": [
        {
            "number": "252.242-7006",
            "title": "Accounting System Administration",
            "text": "The Contractor shall maintain an accounting system that is in compliance with the requirements of this clause. The Contractor's accounting system shall provide for proper segregation of direct costs from indirect costs.",
            "prescription": "DFARS 242.7503",
        },
    ],
    "intellectual_property": [
        {
            "number": "252.227-7013",
            "title": "Rights in Technical Data - Noncommercial Items",
            "text": "The Government shall have unlimited rights in technical data that are developed exclusively with Government funds. The Contractor shall have the right to use, release, or disclose technical data that are developed exclusively at private expense.",
            "prescription": "DFARS 227.7103-6(a)",
            "flowdown": True,
        },
        {
            "number": "252.227-7014",
            "title": "Rights in Other Than Commercial Computer Software and Other Than Commercial Computer Software Documentation",
            "text": "The Government shall have unlimited rights in computer software developed exclusively with Government funds. The Contractor may assert restrictions on the Government's rights to use computer software developed at private expense.",
            "prescription": "DFARS 227.7203-6(a)(1)",
            "flowdown": True,
        },
    ],
    "supply_chain": [
        {
            "number": "252.204-7018",
            "title": "Prohibition on the Acquisition of Covered Telecommunications Equipment or Services - Representation",
            "text": "The Offeror is required to represent whether it does or does not provide covered telecommunications equipment or services as a part of its offered products or services to the Government.",
            "prescription": "DFARS 204.2105(a)",
        },
        {
            "number": "252.225-7009",
            "title": "Restriction on Acquisition of Certain Articles Containing Specialty Metals",
            "text": "Any specialty metals incorporated in items delivered under this contract shall be melted or produced in the United States, its outlying areas, or a qualifying country.",
            "prescription": "DFARS 225.7003-5(a)(1)",
            "flowdown": True,
        },
        {
            "number": "252.225-7012",
            "title": "Preference for Certain Domestic Commodities",
            "text": "The Contractor shall deliver under this contract only domestic items for the classes of commodities specified.",
            "prescription": "DFARS 225.7002-3(a)",
        },
    ],
    "security": [
        {
            "number": "252.204-7000",
            "title": "Disclosure of Information",
            "text": "The Contractor shall not release to anyone outside the Contractor's organization any unclassified information, regardless of medium, pertaining to any part of this contract unless the Contracting Officer has given prior written approval.",
            "prescription": "DFARS 204.404-70(a)",
            "flowdown": True,
        },
        {
            "number": "252.204-7009",
            "title": "Limitations on the Use or Disclosure of Third-Party Contractor Reported Cyber Incident Information",
            "text": "The Contractor shall only use, release, or disclose information obtained from a third-party contractor cyber incident report to assist the Government in investigating and resolving the cyber incident.",
            "prescription": "DFARS 204.7304(b)",
        },
    ],
    "subcontracting": [
        {
            "number": "252.244-7001",
            "title": "Contractor Purchasing System Administration",
            "text": "The Contractor shall maintain a purchasing system that is in compliance with the requirements of this clause. The Contractor purchasing system shall provide for adequate price competition or cost analysis for the subcontract or purchase order.",
            "prescription": "DFARS 244.305-70",
        },
    ],
}

# Flowdown clauses that must be passed to subcontractors
MANDATORY_FLOWDOWN_CLAUSES = [
    "252.204-7012",  # Cyber incident reporting
    "252.204-7021",  # CMMC requirements
    "252.225-7048",  # Export control
    "252.204-7000",  # Disclosure of information
    "252.227-7013",  # Rights in technical data
    "252.227-7014",  # Rights in computer software
    "252.225-7009",  # Specialty metals
    "52.222-26",     # Equal opportunity
    "52.222-50",     # Combating trafficking
    "52.219-8",      # Small business utilization
]

# NAICS codes for defense contracting
NAICS_CODES = {
    "541330": "Engineering Services",
    "541511": "Custom Computer Programming Services",
    "541512": "Computer Systems Design Services",
    "541513": "Computer Facilities Management Services",
    "541519": "Other Computer Related Services",
    "541611": "Administrative Management Consulting",
    "541612": "Human Resources Consulting",
    "541614": "Process and Logistics Consulting",
    "541690": "Other Scientific and Technical Consulting",
    "541715": "Research and Development in the Physical, Engineering, and Life Sciences",
    "541990": "All Other Professional, Scientific, and Technical Services",
    "561110": "Office Administrative Services",
    "561210": "Facilities Support Services",
    "561612": "Security Guards and Patrol Services",
    "611430": "Professional and Management Development Training",
}

# Product/Service Codes
PSC_CODES = {
    "D302": "IT and Telecom - Systems Development",
    "D306": "IT and Telecom - Systems Analysis",
    "D307": "IT and Telecom - IT Strategy and Architecture",
    "D310": "IT and Telecom - Cyber Security",
    "D316": "IT and Telecom - IT Network Management",
    "D399": "IT and Telecom - Other IT and Telecommunications",
    "R408": "Support - Program Management/Support",
    "R425": "Support - Engineering and Technical",
    "R499": "Support - Other Professional Services",
    "R706": "Support - Logistics Support",
    "R710": "Support - Systems Engineering",
    "B541": "Special Studies and Analysis - Defense",
    "AD26": "Technical Assistance - Other",
}

"""Single source of truth for industries, role types, work arrangements and terms."""

INDUSTRIES = {
    "aerospace_defense": "Aerospace & Defense",
    "space": "Space",
    "automotive_mobility": "Automotive & Mobility",
    "software_internet": "Software & Internet",
    "semiconductors_hardware": "Semiconductors & Hardware",
    "biotech_pharma": "Biotech & Pharma",
    "medical_devices": "Medical Devices",
    "energy_climate": "Energy & Climate",
    "robotics_automation": "Robotics & Automation",
    "manufacturing_industrial": "Manufacturing & Industrial",
    "civil_infrastructure": "Civil & Infrastructure",
    "research_labs": "Research & National Labs",
    "quant_fintech": "Quant & Fintech",
}
OTHER = "other"

ROLE_TYPE_GROUPS = {
    "Engineering": {
        "mechanical": "Mechanical",
        "electrical": "Electrical",
        "aerospace": "Aerospace",
        "civil_structural": "Civil & Structural",
        "chemical": "Chemical",
        "biomedical": "Biomedical",
        "industrial_manufacturing": "Industrial & Manufacturing",
        "materials": "Materials",
        "environmental": "Environmental",
        "controls_gnc": "Controls & GNC",
        "embedded_firmware": "Embedded Firmware",
        "test_integration": "Test & Integration",
    },
    "Technology": {
        "software": "Software",
        "data_ml": "Data & ML",
        "cybersecurity": "Cybersecurity",
        "it_infrastructure": "IT & Infrastructure",
        "computer_hardware": "Computer Hardware",
    },
    "Science & Math": {
        "biology_lab": "Biology Lab",
        "chemistry_lab": "Chemistry Lab",
        "physics": "Physics",
        "earth_environmental_science": "Earth & Environmental Science",
        "math_statistics": "Math & Statistics",
    },
}
ROLE_TYPES = {code: label for group in ROLE_TYPE_GROUPS.values() for code, label in group.items()}
NON_STEM = "non_stem"

WORK_ARRANGEMENTS = {
    "in_person": "In person",
    "hybrid": "Hybrid",
    "remote": "Remote",
    "not_stated": "Not stated",
}

# Update after this recruiting cycle (see CLAUDE.md open questions).
SUPPORTED_TERMS = ("Summer 2027", "Fall 2026", "Spring 2027")


def recruiter_domain(role_type: str, industry: str) -> str:
    role = ROLE_TYPES[role_type].lower().replace("&", "and") + " roles"
    if industry == OTHER:
        return role
    return f"{role} at {INDUSTRIES[industry].lower().replace('&', 'and')} companies"

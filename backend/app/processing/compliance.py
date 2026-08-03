POPIA_WEIGHTS = {
    "data_inventory": 0.15,
    "consent": 0.15,
    "purpose_limitation": 0.10,
    "data_quality": 0.10,
    "security_safeguards": 0.30,
    "breach_response": 0.10,
    "data_subject_rights": 0.05,
    "cross_border": 0.05,
}

ISO_WEIGHTS = {
    "A.5_ISMS": 0.20,
    "A.6_organisation": 0.10,
    "A.7_HR": 0.05,
    "A.8_assets": 0.10,
    "A.9_access": 0.10,
    "A.10_crypto": 0.05,
    "A.11_physical": 0.05,
    "A.12_operations": 0.10,
    "A.13_communications": 0.10,
    "A.14_acquisition": 0.05,
    "A.15_supplier": 0.05,
    "A.16_incident": 0.05,
}

def compute_framework_score(domain_scores: dict[str, float], weights: dict[str, float]) -> float:
    score = 0.0
    for domain, pct in domain_scores.items():
        weight = weights.get(domain, 0)
        score += weight * pct
    return round(score, 1)

def compute_popia_score(domain_scores: dict[str, float]) -> float:
    return compute_framework_score(domain_scores, POPIA_WEIGHTS)

def compute_iso_score(theme_scores: dict[str, float]) -> float:
    return compute_framework_score(theme_scores, ISO_WEIGHTS)

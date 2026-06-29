# NCCI Rule Engine for ICD-10-CM coding validation

# Codes that cannot be primary diagnosis (manifestation codes)
# Must always be paired with an underlying condition code
MANIFESTATION_CODES = {
    "E08": "Diabetes due to underlying condition",
    "E09": "Drug or chemical induced diabetes",
    "F02": "Dementia in other diseases",
    "G26": "Extrapyramidal disorders in diseases",
    "G46": "Vascular syndromes of brain in cerebrovascular diseases",
    "G53": "Cranial nerve disorders in diseases",
    "G55": "Nerve root compressions in diseases",
    "G63": "Polyneuropathy in diseases",
    "G73": "Disorders of myoneural junction in diseases",
    "G94": "Other disorders of brain in diseases",
    "H22": "Disorders of iris in diseases",
    "H28": "Cataract in diseases",
    "H32": "Chorioretinal disorders in diseases",
    "H36": "Retinal disorders in diseases",
    "H42": "Glaucoma in diseases",
    "I32": "Pericarditis in diseases",
    "I39": "Endocarditis in diseases",
    "I41": "Myocarditis in diseases",
    "I43": "Cardiomyopathy in diseases",
    "I52": "Other heart disorders in diseases",
    "J17": "Pneumonia in diseases",
    "J91": "Pleural effusion in conditions",
    "J99": "Respiratory disorders in diseases",
    "K23": "Disorders of esophagus in diseases",
    "K67": "Disorders of peritoneum in infectious diseases",
    "K77": "Liver disorders in diseases",
    "K87": "Disorders of gallbladder in diseases",
    "M01": "Direct infections of joint in infectious diseases",
    "M03": "Post-infective arthropathies in diseases",
    "M07": "Enteropathic arthropathies",
    "M09": "Juvenile arthritis in diseases",
    "M14": "Arthropathies in other diseases",
    "M36": "Systemic disorders of connective tissue in diseases",
    "M49": "Spondylopathies in diseases",
    "M63": "Disorders of muscle in diseases",
    "M68": "Disorders of synovium in diseases",
    "M73": "Soft tissue disorders in diseases",
    "M82": "Osteoporosis in diseases",
    "M90": "Osteopathies in diseases",
    "N08": "Glomerular disorders in diseases",
    "N16": "Renal tubulo-interstitial disorders in diseases",
    "N22": "Calculus of urinary tract in diseases",
    "N29": "Other disorders of kidney in diseases",
    "N33": "Bladder disorders in diseases",
    "N37": "Urethral disorders in diseases",
    "N51": "Disorders of male genital organs in diseases",
    "N74": "Female pelvic inflammatory disorders in diseases",
    "N77": "Vulvovaginal ulceration in diseases",
}

# Code pairs that conflict — cannot be billed together
CONFLICTING_PAIRS = [
    ("I10", "I11"),   # Hypertension + Hypertensive heart disease
    ("I10", "I12"),   # Hypertension + Hypertensive CKD
    ("I10", "I13"),   # Hypertension + Hypertensive heart and CKD
    ("E119", "E1165"), # T2DM without complications + T2DM with hyperglycemia
    ("J189", "J17"),  # Pneumonia unspecified + Pneumonia in diseases
    ("J449", "J441"), # COPD unspecified + COPD with exacerbation
    ("J449", "J440"), # COPD unspecified + COPD with lower respiratory infection
    ("I509", "I5022"), # Heart failure unspecified + Chronic systolic HF
    ("I509", "I5032"), # Heart failure unspecified + Chronic diastolic HF
]

# Codes that should always be primary when present
PRIMARY_PRIORITY_CODES = {
    "J189": 1,   # Pneumonia — always primary
    "I214": 1,   # STEMI — always primary
    "I213": 1,   # STEMI — always primary
    "A419": 1,   # Sepsis — always primary
    "J960": 1,   # Acute respiratory failure — always primary
    "I639": 1,   # Stroke — always primary
}

# Symptom codes that should not be coded when a definitive diagnosis exists
SYMPTOM_CODES = {
    "R0600", "R0602", "R0609",  # Dyspnea/shortness of breath
    "R051", "R053", "R05",      # Cough
    "R100", "R104", "R109",     # Abdominal pain
    "R110", "R111", "R112",     # Nausea/vomiting
    "R509", "R5081",            # Fever
    "R0000", "R0001", "R008",   # Heart rate abnormalities
    "R410", "R411", "R4182",    # Cognitive symptoms
}

# Definitive diagnosis codes that make symptom codes redundant
DEFINITIVE_DIAGNOSES = {
    "J189", "J440", "J441", "J449",  # Respiratory
    "I10", "I110", "I119",           # Cardiac
    "I5022", "I5032", "I509",        # Heart failure
    "E119", "E1165",                 # Diabetes
    "N189", "N181",                  # CKD
    "A419",                          # Sepsis
}


def check_manifestation_codes(suggested_codes):
    """Flag codes that cannot stand alone as primary diagnosis."""
    warnings = []
    codes = [s["primary_code"] for s in suggested_codes]

    for suggestion in suggested_codes:
        code = suggestion["primary_code"]
        prefix3 = code[:3]
        prefix2 = code[:2] if len(code) >= 2 else ""

        if prefix3 in MANIFESTATION_CODES:
            warnings.append({
                "code": code,
                "rule": "MANIFESTATION_CODE",
                "message": f"{code} is a manifestation code and requires an underlying condition code.",
                "severity": "warning"
            })

    return warnings


def check_conflicting_pairs(suggested_codes):
    """Check for codes that cannot be billed together."""
    warnings = []
    codes = set(s["primary_code"] for s in suggested_codes)

    for pair in CONFLICTING_PAIRS:
        if pair[0] in codes and pair[1] in codes:
            warnings.append({
                "codes": list(pair),
                "rule": "CONFLICTING_PAIR",
                "message": f"Codes {pair[0]} and {pair[1]} cannot be billed together. Use the more specific code.",
                "severity": "error"
            })

    return warnings


def check_symptom_redundancy(suggested_codes):
    """Remove symptom codes when definitive diagnosis exists."""
    codes = set(s["primary_code"] for s in suggested_codes)
    has_definitive = any(c in DEFINITIVE_DIAGNOSES for c in codes)
    warnings = []

    if has_definitive:
        for suggestion in suggested_codes:
            if suggestion["primary_code"] in SYMPTOM_CODES:
                warnings.append({
                    "code": suggestion["primary_code"],
                    "rule": "SYMPTOM_REDUNDANCY",
                    "message": f"{suggestion['primary_code']} ({suggestion['description']}) is redundant when a definitive diagnosis is coded.",
                    "severity": "info"
                })

    return warnings


def sort_by_priority(suggested_codes):
    """Sort codes with primary diagnoses first."""
    def priority_key(s):
        code = s["primary_code"]
        if code in PRIMARY_PRIORITY_CODES:
            return 0
        if code in SYMPTOM_CODES:
            return 2
        return 1

    return sorted(suggested_codes, key=priority_key)


def run_ncci_validation(suggested_codes):
    """Run all NCCI rules and return validated codes with warnings."""
    all_warnings = []

    # Check manifestation codes
    all_warnings.extend(check_manifestation_codes(suggested_codes))

    # Check conflicting pairs
    all_warnings.extend(check_conflicting_pairs(suggested_codes))

    # Check symptom redundancy
    all_warnings.extend(check_symptom_redundancy(suggested_codes))

    # Sort by priority
    sorted_codes = sort_by_priority(suggested_codes)

    return {
        "validated_codes": sorted_codes,
        "ncci_warnings": all_warnings,
        "has_errors": any(w["severity"] == "error" for w in all_warnings),
        "has_warnings": any(w["severity"] == "warning" for w in all_warnings)
    }
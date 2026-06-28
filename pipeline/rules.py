DUPLICATE_EXCLUSIONS = set()


def validate_codes(suggested_codes):
    seen_codes = set()
    validated = []

    for suggestion in suggested_codes:
        code = suggestion["primary_code"]
        if code in seen_codes:
            continue
        seen_codes.add(code)
        suggestion["validation_status"] = "valid"
        validated.append(suggestion)

    return validated


def check_code_conflicts(codes):
    return []
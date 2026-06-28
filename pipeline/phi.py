from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# Initialize engines
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# PHI entity types to detect and remove
PHI_ENTITIES = [
    "PERSON",
    "DATE_TIME",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "LOCATION",
    "US_SSN",
    "MEDICAL_LICENSE",
    "URL",
    "IP_ADDRESS",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "CREDIT_CARD",
    "US_BANK_NUMBER",
    "AGE",
]

# Custom replacement labels
OPERATORS = {
    "PERSON": OperatorConfig("replace", {"new_value": "<PATIENT_NAME>"}),
    "DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"}),
    "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
    "LOCATION": OperatorConfig("replace", {"new_value": "<LOCATION>"}),
    "US_SSN": OperatorConfig("replace", {"new_value": "<SSN>"}),
    "MEDICAL_LICENSE": OperatorConfig("replace", {"new_value": "<LICENSE>"}),
    "AGE": OperatorConfig("replace", {"new_value": "<AGE>"}),
}


def deidentify(text: str) -> dict:
    """
    Remove PHI from clinical note.
    Returns dict with anonymized text and list of detected PHI types.
    """
    try:
        # Detect PHI
        results = analyzer.analyze(
            text=text,
            entities=PHI_ENTITIES,
            language="en"
        )

        # Anonymize
        anonymized = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=OPERATORS
        )

        detected_phi = list(set([r.entity_type for r in results]))

        return {
            "original_text": text,
            "anonymized_text": anonymized.text,
            "phi_detected": detected_phi,
            "phi_count": len(results)
        }

    except Exception as e:
        print(f"PHI de-identification error: {e}")
        return {
            "original_text": text,
            "anonymized_text": text,
            "phi_detected": [],
            "phi_count": 0
        }


def deidentify_text(text: str) -> str:
    """Simple wrapper — returns just the anonymized text."""
    return deidentify(text)["anonymized_text"]
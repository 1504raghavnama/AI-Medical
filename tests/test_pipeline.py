import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline.nlp import extract_medical_phrases, detect_negation
from pipeline.rag import retrieve_codes, rerank_candidates
from pipeline.rules import validate_codes


def test_phrase_extraction():
    note = "Patient has hypertension and chronic kidney disease."
    phrases = extract_medical_phrases(note)
    assert len(phrases) > 0
    assert any("hypertension" in p for p in phrases)
    print(f"PASS — extracted phrases: {phrases}")


def test_negation_detection():
    note = "No evidence of pneumonia."
    result = detect_negation(note, "pneumonia")
    assert result == "negated"
    print(f"PASS — pneumonia correctly negated")


def test_uncertainty_detection():
    note = "History of myocardial infarction."
    result = detect_negation(note, "myocardial infarction")
    assert result == "uncertain"
    print(f"PASS — myocardial infarction correctly uncertain")


def test_affirmed_detection():
    note = "Patient has hypertension."
    result = detect_negation(note, "hypertension")
    assert result == "affirmed"
    print(f"PASS — hypertension correctly affirmed")


def test_validate_codes():
    codes = [
        {"primary_code": "I10", "entity": "hypertension", "confidence": 0.9,
         "description": "Essential hypertension", "status": "affirmed",
         "alternatives": [], "validation_status": "valid"},
        {"primary_code": "I10", "entity": "hypertension", "confidence": 0.9,
         "description": "Essential hypertension", "status": "affirmed",
         "alternatives": [], "validation_status": "valid"},
    ]
    validated = validate_codes(codes)
    assert len(validated) == 1
    print(f"PASS — duplicate code correctly removed")


if __name__ == "__main__":
    test_phrase_extraction()
    test_negation_detection()
    test_uncertainty_detection()
    test_affirmed_detection()
    test_validate_codes()
    print("\nAll tests passed.")
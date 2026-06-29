from pipeline.normalizer import normalize_entities
from fastapi import APIRouter
from datetime import datetime
from pipeline.nlp import extract_medical_entities, detect_negation
from pipeline.rag import retrieve_codes, rerank_candidates
from pipeline.llm import llm_rerank
from pipeline.rules import validate_codes
from pipeline.loader import get_models
from api.schemas import ClinicalNoteRequest, CodeSuggestionResponse, FeedbackRequest
from governance.audit import log_request, log_feedback, get_code_weight, get_feedback_stats
from pipeline.phi import deidentify
from api.fhir_parser import parse_fhir_bundle, parse_hl7_message, create_sample_fhir_bundle, create_sample_hl7
from pipeline.ncci import run_ncci_validation

router = APIRouter()


@router.get("/health")
def health():
    models = get_models()
    return {
        "status": "ok",
        "icd10_codes": len(models.get("icd10_meta", [])),
        "hcpcs_codes": len(models.get("hcpcs_meta", [])),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/analyze", response_model=CodeSuggestionResponse)
def analyze(request: ClinicalNoteRequest):
    models = get_models()
    note = request.note

    # Step 0 — PHI De-identification
    phi_result = deidentify(note)
    clean_note = phi_result["anonymized_text"]
    phi_detected = phi_result["phi_detected"]
    
    # Step 1 — Extract medical entities using scispacy
    entities = extract_medical_entities(clean_note)

    # Step 1b — UMLS Normalization
    normalized = normalize_entities(entities)
    entities = [n["normalized"] for n in normalized]

    # Step 2 — Negation and uncertainty detection
    affirmed, negated, uncertain = [], [], []
    for entity in entities:
        status = detect_negation(clean_note, entity)
        if status == "negated":
            negated.append(entity)
        elif status == "uncertain":
            uncertain.append(entity)
        else:
            affirmed.append(entity)

    # Step 3 — RAG retrieval + reranking + LLM reasoning
    seen_codes = set()
    seen_conditions = set()
    suggested_codes = []

    # Step 4 — Rule validation
    suggested_codes = validate_codes(suggested_codes)

    # Step 4b — NCCI validation
    ncci_result = run_ncci_validation(suggested_codes)
    suggested_codes = ncci_result["validated_codes"]
    ncci_warnings = ncci_result["ncci_warnings"]

    for query in affirmed + uncertain:
        # Skip duplicate conditions
        query_lower = query.lower().strip()
        if query_lower in seen_conditions:
            continue
        seen_conditions.add(query_lower)

        # Vector retrieval
        candidates = retrieve_codes(
            query,
            models["icd10_embeddings"],
            models["icd10_meta"],
            top_k=10
        )
        reranked = rerank_candidates(candidates, entity=query)

        # LLM reranking
        best = llm_rerank(query, reranked, clean_note)

        if not best or best["code"] in seen_codes:
            continue

        # If LLM says negated, skip
        if best.get("llm_status") == "negated":
            negated.append(query)
            continue

        seen_codes.add(best["code"])
        suggested_codes.append({
            "entity": query,
            "primary_code": best["code"],
            "description": best["description"],
            "confidence": best["combined_score"],
            "status": best.get("llm_status", "uncertain" if query in uncertain else "affirmed"),
            "llm_reason": best.get("llm_reason", ""),
            "alternatives": [
                {
                    "code": c["code"],
                    "description": c["description"],
                    "confidence": c["combined_score"]
                }
                for c in reranked[1:3]
                if c["code"] != best["code"]
            ],
            "validation_status": "valid"
        })

    # Step 4 — Rule validation
    suggested_codes = validate_codes(suggested_codes)

    # Step 5 — Audit log
    log_request(note, suggested_codes)

    return {
        "note": note,
        "anonymized_note": clean_note,
        "phi_detected": phi_detected,
        "total_suggestions": len(suggested_codes),
        "suggested_codes": suggested_codes,
        "negated_entities": negated,
        "uncertain_entities": uncertain,
        "ncci_warnings": ncci_warnings
    }


@router.post("/feedback")
def feedback(request: FeedbackRequest):
    log_feedback(
        note=request.note,
        entity=request.code,
        code=request.code,
        action=request.action,
        corrected_code=request.corrected_code
    )
    return {
        "status": "received",
        "code": request.code,
        "action": request.action
    }


@router.get("/feedback/stats")
def feedback_stats():
    return get_feedback_stats()

@router.post("/analyze/fhir")
def analyze_fhir(fhir_bundle: dict):
    """Accept FHIR Bundle JSON and extract clinical note for analysis."""
    parsed = parse_fhir_bundle(fhir_bundle)
    if not parsed["success"]:
        return {"error": parsed["error"]}
    if not parsed["clinical_note"]:
        return {"error": "No clinical text found in FHIR bundle"}
    # Run through existing pipeline
    from api.schemas import ClinicalNoteRequest
    request = ClinicalNoteRequest(note=parsed["clinical_note"])
    result = analyze(request)
    result_dict = dict(result) if hasattr(result, '__iter__') else result
    return {
        "fhir_parsed": parsed,
        "analysis": result
    }


@router.post("/analyze/hl7")
def analyze_hl7(payload: dict):
    """Accept HL7 v2 message and extract clinical note for analysis."""
    hl7_text = payload.get("message", "")
    if not hl7_text:
        return {"error": "No HL7 message provided"}
    parsed = parse_hl7_message(hl7_text)
    if not parsed["success"]:
        return {"error": parsed["error"]}
    from api.schemas import ClinicalNoteRequest
    request = ClinicalNoteRequest(note=parsed["clinical_note"])
    result = analyze(request)
    return {
        "hl7_parsed": parsed,
        "analysis": result
    }


@router.get("/sample/fhir")
def sample_fhir():
    """Returns a sample FHIR Bundle for testing."""
    return create_sample_fhir_bundle()


@router.get("/sample/hl7")
def sample_hl7():
    """Returns a sample HL7 message for testing."""
    return {"message": create_sample_hl7()}

@router.get("/validate-code/{code}")
def validate_code(code: str):
    models = get_models()
    code_upper = code.upper().strip()
    
    # Search in ICD-10
    for item in models["icd10_meta"]:
        if item["code"] == code_upper:
            return {
                "valid": True,
                "code": code_upper,
                "description": item["description"],
                "source": "ICD-10"
            }
    
    # Search in HCPCS
    for item in models["hcpcs_meta"]:
        if item["code"] == code_upper:
            return {
                "valid": True,
                "code": code_upper,
                "description": item["description"],
                "source": "HCPCS"
            }
    
    return {"valid": False, "code": code_upper, "description": ""}
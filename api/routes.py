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
        "uncertain_entities": uncertain
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
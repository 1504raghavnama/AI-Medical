from fastapi import APIRouter
from datetime import datetime
from pipeline.nlp import extract_medical_phrases, detect_negation
from pipeline.rag import retrieve_codes, rerank_candidates
from pipeline.rules import validate_codes
from pipeline.loader import get_models
from api.schemas import ClinicalNoteRequest, CodeSuggestionResponse, FeedbackRequest
from governance.audit import log_request

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

    # Step 1 — Extract phrases
    phrases = extract_medical_phrases(note)

    # Step 2 — Negation detection
    affirmed, negated, uncertain = [], [], []
    for phrase in phrases:
        status = detect_negation(note, phrase)
        if status == "negated":
            negated.append(phrase)
        elif status == "uncertain":
            uncertain.append(phrase)
        else:
            affirmed.append(phrase)

    # Step 3 — RAG retrieval + reranking
    seen_codes = set()
    suggested_codes = []

    for query in affirmed + uncertain:
        candidates = retrieve_codes(
            query,
            models["icd10_embeddings"],
            models["icd10_meta"],
            models["w2v"]
        )
        reranked = rerank_candidates(candidates)
        best = reranked[0]

        if best["code"] in seen_codes:
            continue
        seen_codes.add(best["code"])

        suggested_codes.append({
            "entity": query,
            "primary_code": best["code"],
            "description": best["description"],
            "confidence": best["combined_score"],
            "status": "uncertain" if query in uncertain else "affirmed",
            "alternatives": [
                {
                    "code": c["code"],
                    "description": c["description"],
                    "confidence": c["combined_score"]
                }
                for c in reranked[1:3]
            ],
            "validation_status": "valid"
        })

    # Step 4 — Rule validation
    suggested_codes = validate_codes(suggested_codes)

    # Step 5 — Audit log
    log_request(note, suggested_codes)

    return {
        "note": note,
        "total_suggestions": len(suggested_codes),
        "suggested_codes": suggested_codes,
        "negated_entities": negated,
        "uncertain_entities": uncertain
    }


@router.post("/feedback")
def feedback(request: FeedbackRequest):
    return {
        "status": "received",
        "code": request.code,
        "action": request.action
    }
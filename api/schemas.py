from pydantic import BaseModel
from typing import List, Optional


class ClinicalNoteRequest(BaseModel):
    note: str


class AlternativeCode(BaseModel):
    code: str
    description: str
    confidence: float


class CodeSuggestion(BaseModel):
    entity: str
    primary_code: str
    description: str
    confidence: float
    status: str
    llm_reason: str
    alternatives: List[AlternativeCode]
    validation_status: str


class CodeSuggestionResponse(BaseModel):
    note: str
    anonymized_note: str
    phi_detected: List[str]
    total_suggestions: int
    suggested_codes: List[CodeSuggestion]
    negated_entities: List[str]
    uncertain_entities: List[str]


class FeedbackRequest(BaseModel):
    note: str
    code: str
    action: str
    corrected_code: Optional[str] = None
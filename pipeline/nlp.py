import re
import spacy

# Load biomedical NER model
nlp = spacy.load("en_core_sci_lg")

NEGATION_TRIGGERS = [
    "no ", "no evidence of", "without", "denies", "denied",
    "negative for", "not ", "absence of", "ruled out", "rule out",
    "unremarkable for", "free of", "never had", "does not have",
    "did not have"
]

UNCERTAINTY_TRIGGERS = [
    "possible", "possibly", "probable", "probably", "suspected",
    "suspect", "query", "cannot exclude", "may have", "might have",
    "history of", "past history", "past medical history"
]

# Medical abbreviation expansion
ABBREVIATIONS = {
    "copd": "chronic obstructive pulmonary disease",
    "chf": "congestive heart failure",
    "afib": "atrial fibrillation",
    "af": "atrial fibrillation",
    "mi": "myocardial infarction",
    "cad": "coronary artery disease",
    "htn": "hypertension",
    "dm": "diabetes mellitus",
    "ckd": "chronic kidney disease",
    "uti": "urinary tract infection",
    "pe": "pulmonary embolism",
    "dvt": "deep vein thrombosis",
    "cva": "cerebrovascular accident",
    "tia": "transient ischemic attack",
    "gerd": "gastroesophageal reflux disease",
    "hf": "congestive heart failure",
    "cap": "community acquired pneumonia",
    "aki": "acute kidney injury",
    "ards": "acute respiratory distress syndrome",
}


def expand_abbreviations(text):
    words = text.split()
    expanded = []
    for word in words:
        clean = word.lower().strip('.,;:()')
        if clean in ABBREVIATIONS:
            expanded.append(ABBREVIATIONS[clean])
        else:
            expanded.append(word)
    return ' '.join(expanded)


GENERIC_WORDS = {
    'patient', 'history', 'evidence', 'report', 'result',
    'finding', 'note', 'record', 'information', 'data',
    'year', 'old', 'male', 'female', 'man', 'woman',
    'day', 'week', 'month', 'time', 'past', 'medical',
    'chest x-ray', 'x-ray', 'xray', 'chest x ray',
    'scan', 'mri', 'ct scan', 'ultrasound', 'ecg', 'ekg',
    'lab', 'test', 'examination', 'exam', 'imaging',
    'medical history', 'pharmaceutical preparations', 
    'medications', 'metformin', 'medication',
    'unspecified', 'specified', 'acute', 'chronic', 'bilateral',
    'current', 'initial', 'subsequent', 'sequela'
}

def extract_medical_entities(text):
    # Expand abbreviations first
    expanded_text = expand_abbreviations(text)

    # Run scispacy NER
    doc = nlp(expanded_text)

    # Extract entities
    entities = []
    for ent in doc.ents:
        entity_text = ent.text.strip()
        if len(entity_text) > 3:
            entities.append(entity_text)

    # Deduplicate while preserving order
    seen = set()
    unique_entities = []
    for e in entities:
        if e.lower() not in seen:
            seen.add(e.lower())
            unique_entities.append(e)

    # Filter out non-medical generic words
    unique_entities = [
        e for e in unique_entities
        if e.lower() not in GENERIC_WORDS
    ]

    return unique_entities


def detect_negation(text, entity, window=8):
    text_lower = text.lower()
    entity_lower = entity.lower()

    sentences = re.split(r'[.!?]', text_lower)
    for sent in sentences:
        if entity_lower in sent:
            for t in NEGATION_TRIGGERS:
                if t in sent:
                    return 'negated'
            for t in UNCERTAINTY_TRIGGERS:
                if t in sent:
                    return 'uncertain'
            entity_pos = sent.find(entity_lower)
            before_text = ' '.join(sent[:entity_pos].split()[-window:])
            for t in NEGATION_TRIGGERS:
                if t in before_text:
                    return 'negated'
    return 'affirmed'


# Keep for backward compatibility
def extract_medical_phrases(text, max_phrases=6):
    return extract_medical_entities(text)[:max_phrases]
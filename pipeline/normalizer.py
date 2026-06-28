import spacy

UMLS_AVAILABLE = False
nlp_linker = None
_linker_initialized = False


def _init_linker():
    global nlp_linker, UMLS_AVAILABLE, _linker_initialized
    if _linker_initialized:
        return
    _linker_initialized = True
    try:
        print("Loading UMLS entity linker...")
        nlp = spacy.load("en_core_sci_lg")
        nlp.add_pipe("scispacy_linker", config={
            "resolve_abbreviations": True,
            "linker_name": "umls"
        })
        nlp_linker = nlp
        UMLS_AVAILABLE = True
        print("UMLS linker loaded.")
    except Exception as e:
        print(f"UMLS linker not available: {e}")
        try:
            nlp_linker = spacy.load("en_core_sci_lg")
        except:
            nlp_linker = None
        UMLS_AVAILABLE = False
        print("Running without UMLS linking.")


def normalize_entity(entity_text: str) -> dict:
    _init_linker()
    if not UMLS_AVAILABLE or nlp_linker is None:
        return {
            "original": entity_text,
            "cui": None,
            "canonical_name": entity_text,
            "aliases": [],
            "score": 0.0
        }
    try:
        doc = nlp_linker(entity_text)
        results = []
        for ent in doc.ents:
            if ent._.kb_ents:
                top_match = ent._.kb_ents[0]
                cui = top_match[0]
                score = top_match[1]
                linker = nlp_linker.get_pipe("scispacy_linker")
                concept = linker.kb.cui_to_entity.get(cui)
                if concept:
                    results.append({
                        "original": entity_text,
                        "cui": cui,
                        "canonical_name": concept.canonical_name,
                        "aliases": list(concept.aliases[:3]),
                        "score": round(score, 4)
                    })
        if results:
            return results[0]
        else:
            return {
                "original": entity_text,
                "cui": None,
                "canonical_name": entity_text,
                "aliases": [],
                "score": 0.0
            }
    except Exception as e:
        print(f"Normalization error for '{entity_text}': {e}")
        return {
            "original": entity_text,
            "cui": None,
            "canonical_name": entity_text,
            "aliases": [],
            "score": 0.0
        }


def normalize_entities(entities: list) -> list:
    normalized = []
    for entity in entities:
        result = normalize_entity(entity)
        normalized.append({
            "original": entity,
            "normalized": result["canonical_name"],
            "cui": result["cui"],
            "score": result["score"]
        })
    return normalized
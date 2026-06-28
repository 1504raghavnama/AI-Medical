import spacy
import scispacy
from scispacy.linking import EntityLinker

print("Loading UMLS entity linker...")
nlp_linker = spacy.load("en_core_sci_lg")
nlp_linker.add_pipe("scispacy_linker", config={
    "resolve_abbreviations": True,
    "linker_name": "umls"
})
print("UMLS linker loaded.")


def normalize_entity(entity_text: str) -> dict:
    """
    Normalize a medical entity to UMLS concepts.
    Returns the best matching UMLS concept with CUI and canonical name.
    """
    try:
        doc = nlp_linker(entity_text)
        results = []

        for ent in doc.ents:
            if ent._.kb_ents:
                top_match = ent._.kb_ents[0]
                cui = top_match[0]
                score = top_match[1]

                # Get canonical name from linker
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
    """
    Normalize a list of entities.
    Returns list of normalized entities with canonical names.
    """
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
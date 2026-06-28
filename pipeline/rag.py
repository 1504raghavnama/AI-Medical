import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Load biomedical sentence transformer
print("Loading PubMedBERT embeddings model...")
embedding_model = SentenceTransformer("pritamdeka/S-PubMedBert-MS-MARCO")
print("PubMedBERT loaded.")

DIRECT_MAPPINGS = {
    "community acquired pneumonia": "J189",
    "community-acquired pneumonia": "J189",
    "pneumonia": "J189",
    "cap": "J189",
    "copd": "J449",
    "chronic obstructive pulmonary disease": "J449",
    "chronic obstructive airway disease": "J449",
    "congestive heart failure": "I509",
    "heart failure": "I509",
    "chf": "I509",
    "atrial fibrillation": "I4891",
    "hypertension": "I10",
    "essential hypertension": "I10",
    "diabetes mellitus": "E119",
    "type 2 diabetes": "E119",
    "diabetes mellitus, non-insulin-dependent": "E119",
    "chronic kidney disease": "N189",
    "myocardial infarction": "I2510",
    "pulmonary embolism": "I2699",
    "deep vein thrombosis": "I8240",
    "sepsis": "A419",
    "urinary tract infection": "N390",
    "stroke": "I6354",
    "pneumonia unspecified": "J189",
}


def check_direct_mapping(query, meta):
    query_lower = query.lower().strip()
    if query_lower in DIRECT_MAPPINGS:
        target_code = DIRECT_MAPPINGS[query_lower]
        for item in meta:
            if item["code"] == target_code:
                return {
                    "code": item["code"],
                    "description": item["description"],
                    "score": 1.0,
                    "combined_score": 1.0
                }
    return None


def get_embedding(text):
    return embedding_model.encode([text])[0]


def get_embeddings_batch(texts):
    return embedding_model.encode(texts, batch_size=64, show_progress_bar=False)


def retrieve_codes(query, embeddings, meta, top_k=10, w2v=None):
    # Check direct mapping first
    direct = check_direct_mapping(query, meta)

    query_vec = get_embedding(query).reshape(1, -1)
    scores = cosine_similarity(query_vec, embeddings)[0]
    top_indices = np.argsort(scores)[::-1][:top_k]

    candidates = [
        {
            "code": meta[i]["code"],
            "description": meta[i]["description"],
            "score": round(float(scores[i]), 4)
        }
        for i in top_indices
    ]

    # Inject direct mapping as first candidate if found
    if direct:
        candidates = [c for c in candidates if c["code"] != direct["code"]]
        candidates.insert(0, direct)
        candidates = candidates[:top_k]

    return candidates


def code_specificity(code):
    return min(len(code.replace('.', '')) / 8.0, 1.0)


def rerank_candidates(candidates, rag_weight=0.92, spec_weight=0.08):
    for c in candidates:
        if "combined_score" not in c:
            c['combined_score'] = round(
                rag_weight * c['score'] + spec_weight * code_specificity(c['code']), 4)
    return sorted(candidates, key=lambda x: x['combined_score'], reverse=True)
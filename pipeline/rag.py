import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def get_embedding(text, w2v):
    words = text.lower().split()
    vecs = [w2v.wv[w] for w in words if w in w2v.wv]
    return np.mean(vecs, axis=0) if vecs else np.zeros(w2v.vector_size)


def retrieve_codes(query, embeddings, meta, w2v, top_k=5):
    query_vec = get_embedding(query, w2v).reshape(1, -1)
    scores = cosine_similarity(query_vec, embeddings)[0]
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [
        {
            "code": meta[i]["code"],
            "description": meta[i]["description"],
            "score": round(float(scores[i]), 4)
        }
        for i in top_indices
    ]


def code_specificity(code):
    return min(len(code.replace('.', '')) / 8.0, 1.0)


def rerank_candidates(candidates, rag_weight=0.92, spec_weight=0.08):
    for c in candidates:
        c['combined_score'] = round(
            rag_weight * c['score'] + spec_weight * code_specificity(c['code']), 4)
    return sorted(candidates, key=lambda x: x['combined_score'], reverse=True)
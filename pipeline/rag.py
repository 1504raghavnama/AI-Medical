import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Load biomedical sentence transformer
print("Loading PubMedBERT embeddings model...")
embedding_model = SentenceTransformer("pritamdeka/S-PubMedBert-MS-MARCO")
print("PubMedBERT loaded.")


def get_embedding(text):
    return embedding_model.encode([text])[0]


def get_embeddings_batch(texts):
    return embedding_model.encode(texts, batch_size=64, show_progress_bar=False)


def retrieve_codes(query, embeddings, meta, top_k=5, w2v=None):
    query_vec = get_embedding(query).reshape(1, -1)
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
import json
import numpy as np
import torch
import torch.nn as nn
from torchcrf import CRF
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity
from config import (
    BILSTM_MODEL_PATH, WORD2VEC_MODEL_PATH,
    WORD2IDX_PATH, TAG2IDX_PATH, MODEL_INFO_PATH,
    ICD10_PATH, HCPCS_PATH
)

# ── BiLSTM-CRF Model Definition ──────────────────────────────────
class BiLSTM_CRF(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_dim, num_tags):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.bilstm = nn.LSTM(embed_dim, hidden_dim // 2, num_layers=2,
                              bidirectional=True, batch_first=True, dropout=0.3)
        self.dropout = nn.Dropout(0.3)
        self.fc = nn.Linear(hidden_dim, num_tags)
        self.crf = CRF(num_tags, batch_first=True)

    def forward(self, x, tags=None, mask=None):
        embed = self.dropout(self.embedding(x))
        lstm_out, _ = self.bilstm(embed)
        lstm_out = self.dropout(lstm_out)
        emissions = self.fc(lstm_out)
        if tags is not None:
            return -self.crf(emissions, tags, mask=mask, reduction="mean")
        return self.crf.decode(emissions, mask=mask)


# ── Global model state ────────────────────────────────────────────
models = {}


def load_all():
    global models

    device = torch.device("cpu")

    # Load vocabularies
    with open(WORD2IDX_PATH) as f:
        word2idx = json.load(f)
    with open(TAG2IDX_PATH) as f:
        tag2idx = json.load(f)
    with open(MODEL_INFO_PATH) as f:
        info = json.load(f)

    idx2tag = {int(v): k for k, v in tag2idx.items()}

    # Load BiLSTM-CRF
    ner_model = BiLSTM_CRF(
        vocab_size=len(word2idx),
        embed_dim=info["embed_dim"],
        hidden_dim=info["hidden_dim"],
        num_tags=len(tag2idx)
    ).to(device)
    ner_model.load_state_dict(torch.load(BILSTM_MODEL_PATH, map_location=device))
    ner_model.eval()

    # Load Word2Vec
    w2v = Word2Vec.load(str(WORD2VEC_MODEL_PATH))

    # Load ICD-10 knowledge base
    with open(ICD10_PATH) as f:
        icd10_meta = json.load(f)

    # Load HCPCS knowledge base
    with open(HCPCS_PATH) as f:
        hcpcs_meta = json.load(f)

    # Pre-compute ICD-10 embeddings
    print("Computing ICD-10 embeddings...")
    icd10_embeddings = _compute_embeddings(icd10_meta, w2v)

    # Pre-compute HCPCS embeddings
    print("Computing HCPCS embeddings...")
    hcpcs_embeddings = _compute_embeddings(hcpcs_meta, w2v)

    models = {
        "device": device,
        "word2idx": word2idx,
        "tag2idx": tag2idx,
        "idx2tag": idx2tag,
        "ner": ner_model,
        "w2v": w2v,
        "icd10_meta": icd10_meta,
        "icd10_embeddings": icd10_embeddings,
        "hcpcs_meta": hcpcs_meta,
        "hcpcs_embeddings": hcpcs_embeddings,
    }

    print(f"Models loaded — ICD-10: {len(icd10_meta)} codes, HCPCS: {len(hcpcs_meta)} codes")
    return models


def _compute_embeddings(meta, w2v):
    embeddings = []
    for item in meta:
        words = item["description"].lower().split()
        vecs = [w2v.wv[w] for w in words if w in w2v.wv]
        if vecs:
            embeddings.append(np.mean(vecs, axis=0))
        else:
            embeddings.append(np.zeros(w2v.vector_size))
    return np.array(embeddings)


def get_models():
    return models
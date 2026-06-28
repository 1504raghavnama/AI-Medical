import json
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from torchcrf import CRF
from pipeline.normalizer import nlp_linker
from sentence_transformers import SentenceTransformer
from config import (
    BILSTM_MODEL_PATH, WORD2VEC_MODEL_PATH,
    WORD2IDX_PATH, TAG2IDX_PATH, MODEL_INFO_PATH,
    ICD10_PATH, HCPCS_PATH
)

CACHE_DIR = Path("./cache")


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


models = {}


def load_all():
    global models

    CACHE_DIR.mkdir(exist_ok=True)
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
    ner_model.load_state_dict(torch.load(
        BILSTM_MODEL_PATH, map_location=device))
    ner_model.eval()

    # Load PubMedBERT
    print("Loading PubMedBERT...")
    embedding_model = SentenceTransformer("pritamdeka/S-PubMedBert-MS-MARCO")
    print("PubMedBERT loaded.")

    # Load knowledge bases
    with open(ICD10_PATH) as f:
        icd10_meta = json.load(f)
    with open(HCPCS_PATH) as f:
        hcpcs_meta = json.load(f)

    # ICD-10 embeddings — load from cache or compute
    icd10_cache = CACHE_DIR / "icd10_embeddings.npy"
    if icd10_cache.exists():
        print("Loading ICD-10 embeddings from cache...")
        icd10_embeddings = np.load(str(icd10_cache))
        print(f"Loaded {len(icd10_embeddings)} ICD-10 embeddings from cache.")
    else:
        print("Computing ICD-10 embeddings (one-time, takes ~1 hour on CPU)...")
        icd10_descriptions = [item["description"] for item in icd10_meta]
        icd10_embeddings = embedding_model.encode(
            icd10_descriptions,
            batch_size=256,
            show_progress_bar=True
        )
        np.save(str(icd10_cache), icd10_embeddings)
        print("ICD-10 embeddings saved to cache.")

    # HCPCS embeddings — load from cache or compute
    hcpcs_cache = CACHE_DIR / "hcpcs_embeddings.npy"
    if hcpcs_cache.exists():
        print("Loading HCPCS embeddings from cache...")
        hcpcs_embeddings = np.load(str(hcpcs_cache))
        print(f"Loaded {len(hcpcs_embeddings)} HCPCS embeddings from cache.")
    else:
        print("Computing HCPCS embeddings...")
        hcpcs_descriptions = [item["description"] for item in hcpcs_meta]
        hcpcs_embeddings = embedding_model.encode(
            hcpcs_descriptions,
            batch_size=256,
            show_progress_bar=True
        )
        np.save(str(hcpcs_cache), hcpcs_embeddings)
        print("HCPCS embeddings saved to cache.")

    models = {
        "device": device,
        "word2idx": word2idx,
        "tag2idx": tag2idx,
        "idx2tag": idx2tag,
        "ner": ner_model,
        "embedding_model": embedding_model,
        "icd10_meta": icd10_meta,
        "icd10_embeddings": icd10_embeddings,
        "hcpcs_meta": hcpcs_meta,
        "hcpcs_embeddings": hcpcs_embeddings,
    }

    print(f"All models loaded — ICD-10: {len(icd10_meta)} codes, HCPCS: {len(hcpcs_meta)} codes")
    return models


def get_models():
    return models
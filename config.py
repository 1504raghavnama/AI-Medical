import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
MODEL_DIR = Path(os.getenv("MODEL_DIR", "./models"))
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", "./knowledge"))

# Model file paths
BILSTM_MODEL_PATH = MODEL_DIR / "bilstm_crf_best.pt"
WORD2VEC_MODEL_PATH = MODEL_DIR / "medical_word2vec.model"
WORD2IDX_PATH = MODEL_DIR / "word2idx.json"
TAG2IDX_PATH = MODEL_DIR / "tag2idx.json"
MODEL_INFO_PATH = MODEL_DIR / "model_info.json"

# Knowledge base paths
ICD10_PATH = KNOWLEDGE_DIR / "icd10" / "icd10_codes_2026.json"
HCPCS_PATH = KNOWLEDGE_DIR / "hcpcs" / "hcpcs_codes.json"

# App settings
DEBUG = os.getenv("DEBUG", "False") == "True"
API_HOST = "0.0.0.0"
API_PORT = 8000
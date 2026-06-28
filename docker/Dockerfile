FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install torch CPU FIRST before anything else
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining packages
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    python-dotenv \
    numpy \
    scikit-learn \
    gensim \
    groq \
    presidio-analyzer \
    presidio-anonymizer \
    fhir.resources \
    pytorch-crf \
    sqlalchemy

# Install sentence-transformers after torch CPU is locked in
RUN pip install --no-cache-dir sentence-transformers

# Install spacy and models
RUN pip install --no-cache-dir spacy scispacy
RUN python -m spacy download en_core_web_lg
RUN pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz

# Pre-download UMLS data
RUN python -c "import scispacy; import spacy; nlp = spacy.load('en_core_sci_lg'); nlp.add_pipe('scispacy_linker', config={'resolve_abbreviations': True, 'linker_name': 'umls'})" || true

COPY api/ ./api/
COPY pipeline/ ./pipeline/
COPY frontend/ ./frontend/
COPY governance/ ./governance/
COPY knowledge/ ./knowledge/
COPY config.py .
COPY .env .

RUN mkdir -p models cache

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
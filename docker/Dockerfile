FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY pipeline/ ./pipeline/
COPY frontend/ ./frontend/
COPY governance/ ./governance/
COPY config.py .
COPY .env .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
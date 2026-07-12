FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir spacy==3.8.4
COPY spacy_fix4.py /tmp/spacy_fix4.py
RUN python /tmp/spacy_fix4.py
RUN python -m spacy download en_core_web_sm || echo "spacy model download failed - will use fallback"
RUN python -m textblob.download_corpora lite
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
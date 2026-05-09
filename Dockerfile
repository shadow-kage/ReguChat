FROM python:3.11-slim

WORKDIR /app

# Copy only what pip needs to resolve deps — this layer is cached as long as
# pyproject.toml and app/ source are unchanged, even if other files change.
COPY pyproject.toml .
COPY app/ ./app/
RUN pip install --no-cache-dir .

# Bake the embedding model so the container starts without network access.
# This layer is also cached independently of non-dep file changes.
RUN python -c "\
from transformers.utils import logging; logging.set_verbosity_error(); \
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy remaining project files (domains/, docker files, etc.)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

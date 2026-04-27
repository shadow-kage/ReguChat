from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from transformers.utils import logging as hf_logging

# Load environment variables from .env (including HF_TOKEN)
load_dotenv()

# Silence noisy transformer warnings about unexpected keys
hf_logging.set_verbosity_error()

# Use the standard PyTorch backend instead of ONNX/optimum.
# This avoids version incompatibilities between `transformers` and `optimum`.
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def create_embeddings(chunks):

    embeddings = model.encode(
        chunks,
        batch_size=128,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    return embeddings
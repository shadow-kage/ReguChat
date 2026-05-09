import os
import torch
from sentence_transformers import SentenceTransformer
from transformers.utils import logging as hf_logging
from app.config import settings
from app.core.markers import Marker

# pydantic-settings populates settings.hf_token from .env but does not write
# it back into os.environ. huggingface_hub reads only os.environ, so we bridge
# the gap here before the model is loaded.
if settings.hf_token and not os.environ.get("HF_TOKEN"):
    os.environ["HF_TOKEN"] = settings.hf_token

# Suppress noisy "unexpected keys" warnings from transformers.
hf_logging.set_verbosity_error()

_device = "cuda" if torch.cuda.is_available() else "cpu"

if _device == "cpu":
    torch.set_num_threads(os.cpu_count() or 4)

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device=_device)

EMBEDDING_DIM: int = model.get_embedding_dimension()


def create_embeddings(chunks: list[str]):
    """
    Encodes chunks with automatic OOM recovery.
    Halves the batch size on each out-of-memory error, down to a minimum of 8.
    """
    batch_size = 64
    while batch_size >= 8:
        try:
            return model.encode(
                chunks,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except RuntimeError as e:
            if "out of memory" not in str(e).lower():
                raise
            print(f"  {Marker.CROSS} OOM at batch_size={batch_size} — retrying with {batch_size // 2}...")
            if _device == "cuda":
                torch.cuda.empty_cache()
            batch_size //= 2

    raise RuntimeError("Embedding failed: OOM persists at minimum batch size.")

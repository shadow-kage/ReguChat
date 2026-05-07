import os
import torch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from transformers.utils import logging as hf_logging
from _markers import Marker

load_dotenv()

# Suppress noisy "unexpected keys" warnings emitted by transformers when
# loading sentence-transformer weights.
hf_logging.set_verbosity_error()

_device = "cuda" if torch.cuda.is_available() else "cpu"

if _device == "cpu":
    # Maximize parallelism for CPU-bound encoding.
    torch.set_num_threads(os.cpu_count() or 4)

# Standard PyTorch backend; avoids version friction between `optimum` and
# `transformers` that arises when using the ONNX export path.
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

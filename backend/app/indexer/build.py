import os
import sys

import yaml

from app.core.embeddings import EMBEDDING_DIM, create_embeddings
from app.core.faiss_store import FAISSVectorDB
from app.core.markers import Marker
from app.indexer.chunking import chunk_text
from app.indexer.extraction import extract_all_pdfs

_TOTAL_STEPS = 4


def build_domain(domain_yaml_path: str) -> None:
    with open(domain_yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    domain_id = cfg["id"]
    pdf_folder = cfg["pdf_folder"]
    vector_db_path = cfg["vector_db_path"]

    print(f"\nReguChat Indexer — Domain: {domain_id}")
    print("─" * 60)

    os.makedirs(vector_db_path, exist_ok=True)
    step = 0

    step += 1
    print(f"\n[{step}/{_TOTAL_STEPS}] Extracting text from PDF(s)...\n")
    data = extract_all_pdfs(pdf_folder)
    if not data:
        print(f"{Marker.HEAVY_CROSS} No PDFs found. Exiting.")
        return
    print(f"\n{Marker.HEAVY_CHECK} Extracted {len(data)} PDF file(s)")

    step += 1
    print(f"\n[{step}/{_TOTAL_STEPS}] Chunking documents...\n")
    all_chunks: list[dict] = []
    for doc in data:
        if not doc["content"].strip():
            print(f"  {Marker.SKIP} {doc['source']} → skipped (no text extracted)")
            continue
        text_chunks = chunk_text(doc["content"])
        print(f"  {Marker.CHECK} {doc['source']} → {len(text_chunks)} chunks")
        for text in text_chunks:
            all_chunks.append({"text": text, "source": doc["source"]})

    if not all_chunks:
        print(f"\n{Marker.HEAVY_CROSS} No chunks created. Exiting.")
        return
    print(f"\n{Marker.HEAVY_CHECK} Total chunks: {len(all_chunks)}")

    step += 1
    print(f"\n[{step}/{_TOTAL_STEPS}] Creating embeddings...\n")
    texts_only = [c["text"] for c in all_chunks]
    embeddings = create_embeddings(texts_only)

    step += 1
    print(f"\n[{step}/{_TOTAL_STEPS}] Building FAISS index...\n")
    db = FAISSVectorDB(EMBEDDING_DIM)
    db.add(embeddings, all_chunks)
    db.save(vector_db_path)

    print(f"{Marker.HEAVY_CHECK} Done. Vector database saved to: {vector_db_path}\n")


if __name__ == "__main__":
    domain_path = sys.argv[1] if len(sys.argv) > 1 else "domains/medical.yaml"
    build_domain(domain_path)

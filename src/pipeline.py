import os
from extraction import extract_all_pdfs
from chunking import chunk_text
from embeddings import create_embeddings
from faiss_db import FAISSVectorDB
from _markers import Marker

PDF_FOLDER = "data/pdfs"
VECTOR_DB_PATH = "vector_db"
_TOTAL_STEPS = 4


def main():
    # Create output directory upfront — fail fast before any expensive work.
    os.makedirs(VECTOR_DB_PATH, exist_ok=True)

    step = 0

    step += 1
    print(f"\n[{step}/{_TOTAL_STEPS}] Extracting text from PDF(s)...\n")
    data = extract_all_pdfs(PDF_FOLDER)
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
    dim = embeddings.shape[1]

    step += 1
    print(f"\n[{step}/{_TOTAL_STEPS}] Building FAISS index...\n")
    db = FAISSVectorDB(dim)
    db.add(embeddings, all_chunks)
    db.save(VECTOR_DB_PATH)

    print(f"{Marker.HEAVY_CHECK} Done. Vector database saved to: {VECTOR_DB_PATH}\n")


if __name__ == "__main__":
    main()

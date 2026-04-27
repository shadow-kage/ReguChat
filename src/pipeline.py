import os
from extraction import extract_all_pdfs
from chunking import chunk_text
from embeddings import create_embeddings
from faiss_db import FAISSVectorDB


def main():

    pdf_folder = "data/pdfs"
    vector_path = "vector_db"

    print("\nSTEP 1: Extracting text from PDFs\n")

    data = extract_all_pdfs(pdf_folder)

    if not data:
        print("No PDFs found.")
        return

    print(f"Extracted {len(data)} PDF files")

    print("\nSTEP 2: Chunking documents\n")

    all_chunks = []

    for doc in data:

        if not doc["content"].strip():
            continue

        chunks = chunk_text(doc["content"])

        print(f"{doc['source']} → {len(chunks)} chunks")

        all_chunks.extend(chunks)

    print(f"\nTotal chunks created: {len(all_chunks)}")

    if len(all_chunks) == 0:
        print("No chunks created. Exiting.")
        return

    print("\nSTEP 3: Creating embeddings (this may take a few minutes)\n")

    # Show chunk count before embedding
    print(f"Embedding {len(all_chunks)} chunks...")

    embeddings = create_embeddings(all_chunks)

    print("\nEmbeddings created successfully")
    print(f"Total embeddings: {len(embeddings)}")

    dim = len(embeddings[0])

    print("\nSTEP 4: Building FAISS vector database\n")

    db = FAISSVectorDB(dim)

    print("Adding embeddings to FAISS index...")
    db.add(embeddings, all_chunks)

    os.makedirs(vector_path, exist_ok=True)

    print("Saving FAISS index...")
    db.save(vector_path)

    print("\nVector database saved successfully.")
    print(f"Location: {vector_path}")


if __name__ == "__main__":
    main()
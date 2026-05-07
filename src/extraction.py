import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import fitz  # PyMuPDF
from _markers import Marker


def extract_text_from_pdf(pdf_path: str) -> str:
    page_texts = []
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                try:
                    page_texts.append(page.get_text("text"))
                except Exception as e:
                    print(f"  {Marker.CROSS} Page error in {os.path.basename(pdf_path)}: {e}")
    except Exception as e:
        print(f"  {Marker.HEAVY_CROSS} Failed to open {os.path.basename(pdf_path)}: {e}")
    return "".join(page_texts)


def extract_all_pdfs(folder: str) -> list[dict]:
    """
    Extracts text from all PDFs in `folder` concurrently.
    Each file gets its own thread with its own independent fitz open — safe.
    """
    if not os.path.isdir(folder):
        print(f"  {Marker.HEAVY_CROSS} PDF folder not found: {folder}")
        return []

    pdf_files = sorted(f for f in os.listdir(folder) if f.endswith(".pdf"))
    if not pdf_files:
        return []

    def process_file(filename: str) -> dict:
        result = {"source": filename, "content": extract_text_from_pdf(os.path.join(folder, filename))}
        print(f"  {Marker.CHECK} {filename}")
        return result

    workers = min(len(pdf_files), os.cpu_count() or 4)
    results: dict[str, dict] = {}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process_file, f): f for f in pdf_files}
        for future in as_completed(futures):
            filename = futures[future]
            try:
                results[filename] = future.result()
            except Exception as e:
                print(f"  {Marker.CROSS} {filename}: {e}")

    # Restore deterministic order (as_completed gives arbitrary ordering).
    return [results[f] for f in pdf_files if f in results]

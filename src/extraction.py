import fitz
import os

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        doc = fitz.open(pdf_path)

        for page in doc:

            try:
                text += page.get_text("text")

            except Exception as e:
                print(f"Skipping page due to error: {e}")

        doc.close()

    except Exception as e:
        print(f"Failed to open {pdf_path}: {e}")

    return text

def extract_all_pdfs(folder):
    data = []
    for file in os.listdir(folder):

        if file.endswith(".pdf"):

            path = os.path.join(folder, file)

            print(f"Processing: {file}")

            text = extract_text_from_pdf(path)

            data.append({
                "source": file,
                "content": text
            })
    return data
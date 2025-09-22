# modules/rag_loader.py
import fitz
import os

def pdfs_to_txt(pdf_folder="data/documents/", txt_folder="data/documents_txt/"):
    os.makedirs(txt_folder, exist_ok=True)
    for fname in os.listdir(pdf_folder):
        if fname.endswith(".pdf"):
            pdf_path = os.path.join(pdf_folder, fname)
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            txt_name = fname.replace(".pdf", ".txt")
            with open(os.path.join(txt_folder, txt_name), "w", encoding="utf-8") as f:
                f.write(text)
    print(f"✅ Converted all PDFs from {pdf_folder} to TXT in {txt_folder}")

# Optional: call the function directly for testing
if __name__ == "__main__":
    pdfs_to_txt()

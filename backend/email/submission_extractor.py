import os
import docx2txt
from pdfminer.high_level import extract_text as pdf_extract_text

# ---------------- CONFIG ----------------
BASE_DIR = os.path.expanduser("~/Desktop/projects/AI4INSURANCE/backend")
INPUT_FOLDER = os.path.join(BASE_DIR, "comined", "Facultative_Submissions")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "email", "extracted", "Facultative_Submissions")

# Allowed conversion types
CONVERTIBLE_EXTENSIONS = {".pdf", ".docx", ".txt"}
# ----------------------------------------

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file using pdfminer.six"""
    try:
        text = pdf_extract_text(pdf_path)
        return text.strip()
    except Exception as e:
        return f"[Error reading PDF {pdf_path}: {e}]"

def extract_text_from_docx(docx_path):
    """Extract text from DOCX file using docx2txt"""
    try:
        return docx2txt.process(docx_path) or ""
    except Exception as e:
        return f"[Error reading DOCX {docx_path}: {e}]"

def extract_text_from_txt(txt_path):
    """Simply read plain text file"""
    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"[Error reading TXT {txt_path}: {e}]"

def process_submission_folder(input_folder, output_folder):
    """Convert all supported files in a submission folder"""
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(input_folder):
        filepath = os.path.join(input_folder, filename)
        if not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(filename)[1].lower()
        text = None

        if ext == ".pdf":
            text = extract_text_from_pdf(filepath)
        elif ext == ".docx":
            text = extract_text_from_docx(filepath)
        elif ext == ".txt":
            text = extract_text_from_txt(filepath)

        if text is not None:
            # Build output filename with "_converted.txt"
            base_name = os.path.splitext(filename)[0]
            out_name = f"{base_name}_converted.txt"
            out_path = os.path.join(output_folder, out_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"✅ Converted: {filename} -> {out_path}")
        else:
            print(f"❌ Skipped unsupported: {filename}")

def process_all_existing_submissions():
    """Walk through all existing submissions and convert"""
    for root, dirs, files in os.walk(INPUT_FOLDER):
        for dirname in dirs:
            if dirname.startswith("Submission_"):
                in_sub_path = os.path.join(root, dirname)
                # Mirror the structure inside OUTPUT_FOLDER
                rel_path = os.path.relpath(in_sub_path, INPUT_FOLDER)
                out_sub_path = os.path.join(OUTPUT_FOLDER, rel_path)
                print(f"📂 Processing {in_sub_path} -> {out_sub_path}")
                process_submission_folder(in_sub_path, out_sub_path)

if __name__ == "__main__":
    process_all_existing_submissions()

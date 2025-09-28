import os
import re
import json
from dotenv import load_dotenv
from google import genai

# Load .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

# Initialize Gemini client
client = genai.Client(api_key=api_key)
MODEL = "gemini-2.5-flash"

# Base folders
BASE_DIR = os.path.expanduser("~/Desktop/projects/AI4INSURANCE/backend/email")
INPUT_FOLDER = os.path.join(BASE_DIR, "extracted", "Facultative_Submissions")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "nlp2", "merged_json")

# Fields to extract
FIELDS = [
    "Insured", "Cedant", "Broker", "Perils_Covered",
    "Geographical_Limit", "Situation_of_Risk",
    "Occupation_of_Insured", "Main_Activities",
    "TSI_Original_Currency", "Original_Currency",
    "Premium_Original_Currency", "Excess_Deductible",
    "Retention_of_Cedant_Pct", "Share_Offered_Pct", "PML_Pct",
    "Paid_Losses_3_Years", "Outstanding_Reserves_3_Years",
    "Recoveries_3_Years", "Earned_Premium_3_Years",
    "Climate_Change_Risk", "ESG_Risk_Level",
    "Period_Start", "Period_End", "Premium_Rate_Pct",
    "Premium_KES", "Proposed_Terms_Conditions"
]

def clean_json_string(text: str) -> str:
    """Remove backticks and extra markers from JSON response."""
    cleaned = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.IGNORECASE|re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
    return cleaned.strip()

def extract_from_text(text: str) -> dict:
    """Full extraction from Gemini."""
    prompt = (
        "You are an expert insurance underwriter extracting data from facultative reinsurance submissions. "
        "Extract ALL the following fields and return ONLY a valid JSON object with exactly these keys, using null for missing fields.\n\n"
        f"Fields: {FIELDS}\n\n"
        f"Text to process:\n{text}"
    )
    response = client.models.generate_content(model=MODEL, contents=prompt)
    raw = response.text
    cleaned = clean_json_string(raw)
    
    try:
        return json.loads(cleaned)
    except Exception as e:
        print("⚠️ Could not parse JSON:", e)
        return {}

def extract_from_text_two_pass(text: str) -> dict:
    """Two-pass extraction: first full, then focus on missing fields."""
    # --- First pass ---
    full_data = extract_from_text(text)

    # Identify missing fields
    missing_fields = [f for f in FIELDS if f not in full_data or full_data[f] in (None, "", [])]
    if not missing_fields:
        return full_data  # all fields found
    
    # --- Second pass for missing fields ---
    print(f"🔄 Re-running Gemini for missing fields: {missing_fields}")
    focused_prompt = (
        "You are an expert insurance underwriter. The following fields were missing: "
        f"{missing_fields}\n"
        "Extract ONLY these fields from the text below and return a valid JSON with null for anything not found.\n\n"
        f"Text to process:\n{text}"
    )
    response = client.models.generate_content(model=MODEL, contents=focused_prompt)
    cleaned = clean_json_string(response.text)
    
    try:
        focused_data = json.loads(cleaned)
    except Exception as e:
        print("⚠️ Could not parse focused JSON:", e)
        focused_data = {}
    
    # Merge focused data back
    for f in missing_fields:
        if f in focused_data and focused_data[f] not in (None, "", []):
            full_data[f] = focused_data[f]
    
    return full_data

def merge_jsons(json_list):
    """Merge list of JSONs, taking first valid value for each field."""
    merged = {}
    for field in FIELDS:
        for j in json_list:
            if field in j and j[field] not in (None, "", []):
                merged[field] = j[field]
                break
        if field not in merged:
            merged[field] = None
    return merged

def process_submission(sub_folder):
    """Process all .txt files in a submission folder."""
    rel_path = os.path.relpath(sub_folder, INPUT_FOLDER)
    out_path = os.path.join(OUTPUT_FOLDER, rel_path + ".json")
    if os.path.isfile(out_path):
        print(f"⏭️ Skipping {sub_folder} (already processed at {out_path})")
        return

    jsons = []
    for fname in os.listdir(sub_folder):
        if fname.endswith(".txt"):
            txt_path = os.path.join(sub_folder, fname)
            with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if content.strip():
                print(f"🔍 Processing {txt_path} ...")
                data = extract_from_text_two_pass(content)
                jsons.append(data)

    if not jsons:
        print(f"⚠️ No valid text found in {sub_folder}")
        return

    merged = merge_jsons(jsons)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=4)

    print(f"✅ Merged JSON saved: {out_path}")

def process_all_submissions():
    """Walk through all submission folders and process them."""
    for root, dirs, _ in os.walk(INPUT_FOLDER):
        for d in dirs:
            if d.startswith("Submission_"):
                process_submission(os.path.join(root, d))

if __name__ == "__main__":
    process_all_submissions()

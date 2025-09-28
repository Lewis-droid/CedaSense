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

# Initialize the Gemini client
client = genai.Client(api_key=api_key)

# Model to use
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
    "TSI_Original_Currency",  # numeric value only, 0 if unknown
    "Original_Currency",
    "Premium_Original_Currency",  # numeric value only, no commas/letters
    "Excess_Deductible",  # numeric only (use first % or minimum as a number)
    "Retention_of_Cedant_Pct",
    "Share_Offered_Pct",
    "PML_Pct",
    "Paid_Losses_3_Years",
    "Outstanding_Reserves_3_Years",
    "Recoveries_3_Years",
    "Earned_Premium_3_Years",
    "Climate_Change_Risk",
    "ESG_Risk_Level",
    "Period_Start",
    "Period_End",
    "Premium_Rate_Pct",
    "Premium_KES",
    "Proposed_Terms_Conditions"
]

def clean_json_string(text: str) -> str:
    """Remove backticks and extra markers from JSON response."""
    cleaned = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.IGNORECASE|re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE)
    return cleaned.strip()



def extract_from_text(text: str) -> dict:
    """Send text to Gemini API and parse structured JSON with numeric TSI and other numbers."""
    
    prompt = (
        "You are an expert insurance underwriter extracting data from facultative reinsurance submissions. "
        "Extract ALL the following fields from the insurance document text. "
        "Return ONLY a valid JSON object with exactly these keys, no extra text.\n\n"
        
        "CRITICAL RULES:\n"
        "1. ALL fields must be present in the JSON response - use null for missing values\n"
        "2. For numeric fields, return numbers only (no commas, letters, or currency symbols)\n"
        "3. For percentages, return numbers only (e.g., 5% -> 5)\n"
        "4. For monetary amounts, extract the number and put currency code in 'Original_Currency'\n"
        "5. For dates, use YYYY-MM-DD format or 'to be agreed' if not specified\n"
        "6. For missing values, use null (not empty strings or 0)\n"
        "7. Do not include markdown, backticks, or explanations - just JSON\n\n"
        
        "FIELD-SPECIFIC INSTRUCTIONS:\n"
        "- Insured: Company/entity name being insured\n"
        "- Cedant: Insurance company ceding the risk\n"
        "- Broker: Insurance broker handling the placement\n"
        "- Perils_Covered: All covered risks/perils (comprehensive list)\n"
        "- Geographical_Limit: Geographic scope of coverage\n"
        "- Situation_of_Risk: Physical location(s) of the risk\n"
        "- Occupation_of_Insured: Business type/industry\n"
        "- Main_Activities: Primary business activities\n"
        "- TSI_Original_Currency: Total Sum Insured (numeric only)\n"
        "- Original_Currency: Currency code (USD, EUR, KES, etc.)\n"
        "- Premium_Original_Currency: Premium amount (numeric only)\n"
        "- Excess_Deductible: Deductible amount (numeric only)\n"
        "- Retention_of_Cedant_Pct: Percentage retained by cedant (numeric only)\n"
        "- Share_Offered_Pct: Percentage offered to reinsurer (numeric only)\n"
        "- PML_Pct: Probable Maximum Loss percentage (numeric only)\n"
        "- Paid_Losses_3_Years: Total paid losses over 3 years (numeric only, 0 if none)\n"
        "- Outstanding_Reserves_3_Years: Outstanding claim reserves (numeric only, 0 if none)\n"
        "- Recoveries_3_Years: Recoveries from reinsurers (numeric only, 0 if none)\n"
        "- Earned_Premium_3_Years: Earned premium over 3 years (numeric only, 0 if none)\n"
        "- Climate_Change_Risk: Risk assessment level (Low/Medium/High)\n"
        "- ESG_Risk_Level: Environmental/Social/Governance risk level\n"
        "- Period_Start: Coverage start date (YYYY-MM-DD or 'to be agreed')\n"
        "- Period_End: Coverage end date (YYYY-MM-DD or 'to be agreed')\n"
        "- Premium_Rate_Pct: Premium rate percentage (numeric only)\n"
        "- Premium_KES: Premium in Kenyan Shillings (numeric only, 0 if not converted)\n"
        "- Proposed_Terms_Conditions: Key terms and conditions\n\n"
        
        "IMPORTANT: If any field is not found in the document, use null for that field. "
        "Do not guess or make up values. Be thorough in searching the document.\n\n"
        
        f"Text to process:\n{text}"
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    raw = response.text
    cleaned = clean_json_string(raw)

    try:
        parsed = json.loads(cleaned)
        return parsed
    except Exception as e:
        print("⚠️ Could not parse JSON:", e)
        return {}



def merge_jsons(json_list):
    """Merge list of JSONs, taking first valid value for each field."""
    merged = {}
    for field in FIELDS:
        for j in json_list:
            if field in j and j[field] not in (None, "", []):
                merged[field] = j[field]
                break
    return merged

def process_submission(sub_folder):
    """Process all .txt files in a submission folder."""
    # Skip if merged JSON already exists for this submission
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
                data = extract_from_text(content)
                jsons.append(data)

    if not jsons:
        print(f"⚠️ No valid text found in {sub_folder}")
        return

    merged = merge_jsons(jsons)

    # Save merged JSON
    rel_path = os.path.relpath(sub_folder, INPUT_FOLDER)
    out_path = os.path.join(OUTPUT_FOLDER, rel_path + ".json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=4)

    print(f"✅ Merged JSON saved: {out_path}")

def process_all_submissions():
    """Walk through all submission folders and process them."""
    for root, dirs, _ in os.walk(INPUT_FOLDER):
        for d in dirs:
            if d.startswith("Submission_"):
                sub_folder = os.path.join(root, d)
                process_submission(sub_folder)

if __name__ == "__main__":
    process_all_submissions()

import json
import os
import sys
from flask import Flask, jsonify, request, send_from_directory
import importlib.util

# Resolve project structure
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
APIS_DIR = os.path.join(PROJECT_ROOT, "apis")
CALC_DIR = os.path.join(PROJECT_ROOT, "calcultaions")  # note: folder name is 'calcultaions'
FINAL_DIR = os.path.join(PROJECT_ROOT, "FINAL")
FRONTEND_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "frontend"))
EMAIL_DIR = os.path.join(PROJECT_ROOT, "email")
NLP2_DIR = os.path.join(PROJECT_ROOT, "nlp2")

# Ensure importability of project packages
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
 
# Import modules
from apis import code as code_module
from calcultaions import calculator as calc_module
from FINAL import combine as decision_module


# -------------------------------
# Orchestration (from smallmai.py)
# -------------------------------

PATH_TEST2 = os.path.join(EMAIL_DIR, "test2.py")
PATH_SUBMISSION_EXTRACTOR = os.path.join(EMAIL_DIR, "submission_extractor.py")
PATH_APITEST = os.path.join(NLP2_DIR, "APItest.py")


SRC_MERGED_JSON = os.path.join(
    EMAIL_DIR,
    "nlp2",
    "merged_json",
    "2025",
    "09_September",
    "Submission_20250925_204109_gichinga03_at_gmail.com.json",
)


def _load_module_from_path(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_email_receiver():
    mod = _load_module_from_path("email_processor", PATH_TEST2)
    if hasattr(mod, "process_emails"):
        print("\ud83d\udce5 Running email receiver ...")
        mod.process_emails()
    else:
        print("\u26a0\ufe0f process_emails() not found in test2.py")


def run_submission_extractor():
    mod = _load_module_from_path("submission_extractor", PATH_SUBMISSION_EXTRACTOR)
    if hasattr(mod, "process_all_existing_submissions"):
        print("\ud83e\uddfe Extracting text from submissions ...")
        mod.process_all_existing_submissions()
    else:
        print("\u26a0\ufe0f process_all_existing_submissions() not found in submission_extractor.py")


def run_nlp_processing():
    mod = _load_module_from_path("apitest_runner", PATH_APITEST)
    if hasattr(mod, "process_all_submissions"):
        print("\ud83e\udde0 Running NLP processing on extracted text ...")
        mod.process_all_submissions()
    else:
        print("\u26a0\ufe0f process_all_submissions() not found in APItest.py")


def append_merged_json_to_sample_input(src_json_path: str, dest_sample_input_path: str):
    if not os.path.isfile(src_json_path):
        print(f"\u26a0\ufe0f Source JSON not found: {src_json_path}")
        return
    try:
        with open(src_json_path, "r", encoding="utf-8") as f:
            data_obj = json.load(f)
    except Exception as e:
        print(f"\u26a0\ufe0f Failed to read source JSON: {e}")
        return

    dest_data = []
    if os.path.isfile(dest_sample_input_path):
        try:
            with open(dest_sample_input_path, "r", encoding="utf-8") as f:
                dest_data = json.load(f)
            if not isinstance(dest_data, list):
                print("\u26a0\ufe0f Destination JSON is not a list. Aborting append.")
                return
        except Exception as e:
            print(f"\u26a0\ufe0f Failed to read destination JSON, starting new list: {e}")
            dest_data = []

    dest_data.append(data_obj)

    try:
        with open(dest_sample_input_path, "w", encoding="utf-8") as f:
            json.dump(dest_data, f, indent=2, ensure_ascii=False)
        print(f"\u2705 Appended merged JSON into: {dest_sample_input_path}")
    except Exception as e:
        print(f"\u26a0\ufe0f Failed to write destination JSON: {e}")


def run_pipeline():
    # Paths
    os.makedirs(CALC_DIR, exist_ok=True)
    os.makedirs(FINAL_DIR, exist_ok=True)

    input_path = os.path.join(CALC_DIR, "sample_input.json")
    facultative_path = os.path.join(CALC_DIR, "facultative_reinsurance_calculations.json")
    final_path = os.path.join(FINAL_DIR, "decisions.json")

    # 1. Step 1 - run enrichment (code.py)
    print("🔹 Running enrichment (code.py)...")
    risks = code_module.load_input(input_path)
    enriched_records = [code_module.enrich_risk_record(r) for r in risks]
    code_module.write_output(facultative_path, enriched_records)

    # 2. Step 2 - run calculator (calculator.py)
    print("🔹 Running actuarial calculator (calculator.py)...")
    df = calc_module.load_json_input(facultative_path)
    calculator = calc_module.FacultativeReinsuranceCalculator()
    df_calculated = calculator.calculate_all_metrics(df)
    calc_module.save_json_output(df_calculated, facultative_path)

    # 3. Step 3 - run decision engine (combine.py)
    print("🔹 Running decision engine (combine.py)...")
    with open(facultative_path, "r", encoding="utf-8") as f:
        calculated_data = json.load(f)
    decisions = decision_module.score_facultative_risks(calculated_data)

    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2)

    print("\n✅ Pipeline finished successfully!")
    print(f"   Facultative calculations → {facultative_path}")
    print(f"   Final decisions          → {final_path}")

    return final_path


# -------------------------------
# API + Static Frontend Server
# -------------------------------

def launch_web(final_path):
    app = Flask(__name__)

    if not os.path.isdir(FRONTEND_DIR):
        print(f"⚠️ Frontend directory not found: {FRONTEND_DIR}")

    # Minimal CORS for frontend dev
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*") or "*"
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    # API
    @app.route("/api/decisions", methods=["GET", "OPTIONS"])
    def api_decisions():
        if request.method == "OPTIONS":
            return ("", 204)
        try:
            with open(final_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return jsonify({"error": "decisions.json not found"}), 404
        return jsonify(data)

    # Static frontend routes
    @app.route("/")
    def serve_index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/detail.html")
    def serve_detail():
        return send_from_directory(FRONTEND_DIR, "detail.html")

    @app.route("/<path:path>")
    def serve_assets(path):
        return send_from_directory(FRONTEND_DIR, path)

    print("\n🌐 App running at: http://127.0.0.1:5000")
    print(f"   Serving frontend from: {FRONTEND_DIR}")
    print("   API: /api/decisions")
    print("   Frontend: / and /detail.html")
    app.run(debug=True)


if __name__ == "__main__":
    # Orchestrate inbound -> extract -> NLP -> append
    run_email_receiver()
    run_submission_extractor()
    run_nlp_processing()
    append_merged_json_to_sample_input(
        SRC_MERGED_JSON,
        os.path.join(CALC_DIR, "sample_input.json")
    )

    final_path = run_pipeline()
    launch_web(final_path)

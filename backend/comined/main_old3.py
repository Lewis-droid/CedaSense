import json
import os
import sys
import time
import threading
from flask import Flask, jsonify, request, send_from_directory
import importlib.util

# Resolve project structure
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
APIS_DIR = os.path.join(PROJECT_ROOT, "apis")
CALC_DIR = os.path.join(PROJECT_ROOT, "calcultaions")
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

# Paths to scripts
PATH_TEST2 = os.path.join(EMAIL_DIR, "test2.py")
PATH_SUBMISSION_EXTRACTOR = os.path.join(EMAIL_DIR, "submission_extractor.py")
PATH_APITEST = os.path.join(NLP2_DIR, "APItest.py")

# State tracking
last_submission_count = 0
last_extracted_count = 0
final_path = os.path.join(FINAL_DIR, "decisions.json")

def _load_module_from_path(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def count_submission_folders():
    """Count total submission folders in Facultative_Submissions"""
    base_folder = os.path.join(os.getcwd(), "Facultative_Submissions")
    if not os.path.exists(base_folder):
        return 0
    
    count = 0
    for root, dirs, files in os.walk(base_folder):
        for d in dirs:
            if d.startswith("Submission_"):
                count += 1
    return count

def count_extracted_folders():
    """Count total extracted folders"""
    extracted_folder = os.path.join(EMAIL_DIR, "extracted", "Facultative_Submissions")
    if not os.path.exists(extracted_folder):
        return 0
    
    count = 0
    for root, dirs, files in os.walk(extracted_folder):
        for d in dirs:
            if d.startswith("Submission_"):
                count += 1
    return count

def run_email_receiver():
    """Run email receiver and return number of new submissions processed"""
    mod = _load_module_from_path("email_processor", PATH_TEST2)
    if hasattr(mod, "process_emails"):
        print("[EMAIL] Checking for new emails...")
        mod.process_emails()
        return count_submission_folders()
    else:
        print("[WARN] process_emails() not found in test2.py")
        return 0

def run_submission_extractor():
    """Run text extraction on new submissions"""
    mod = _load_module_from_path("submission_extractor", PATH_SUBMISSION_EXTRACTOR)
    if hasattr(mod, "process_all_existing_submissions"):
        print("[EXTRACT] Extracting text from new submissions...")
        mod.process_all_existing_submissions()
        return count_extracted_folders()
    else:
        print("[WARN] process_all_existing_submissions() not found in submission_extractor.py")
        return 0

def run_nlp_processing():
    """Run NLP processing on new extracted content"""
    mod = _load_module_from_path("apitest_runner", PATH_APITEST)
    if hasattr(mod, "process_all_submissions"):
        print("[NLP] Running NLP processing on extracted text...")
        mod.process_all_submissions()
        return True
    else:
        print("[WARN] process_all_submissions() not found in APItest.py")
        return False

def append_latest_merged_json():
    """Find and append the most recent merged JSON to sample_input.json"""
    merged_json_dir = os.path.join(EMAIL_DIR, "nlp2", "merged_json")
    if not os.path.exists(merged_json_dir):
        print("[WARN] No merged JSON directory found")
        return
    
    # Find the most recent JSON file
    latest_json = None
    latest_time = 0
    
    for root, dirs, files in os.walk(merged_json_dir):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                file_time = os.path.getmtime(file_path)
                if file_time > latest_time:
                    latest_time = file_time
                    latest_json = file_path
    
    if not latest_json:
        print("[WARN] No merged JSON files found")
        return
    
    # Append to sample_input.json
    dest_path = os.path.join(CALC_DIR, "sample_input.json")
    
    try:
        with open(latest_json, "r", encoding="utf-8") as f:
            data_obj = json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to read latest JSON: {e}")
        return

    dest_data = []
    if os.path.isfile(dest_path):
        try:
            with open(dest_path, "r", encoding="utf-8") as f:
                dest_data = json.load(f)
            if not isinstance(dest_data, list):
                print("[WARN] Destination JSON is not a list. Aborting append.")
                return
        except Exception as e:
            print(f"[WARN] Failed to read destination JSON, starting new list: {e}")
            dest_data = []

    dest_data.append(data_obj)

    try:
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(dest_data, f, indent=2, ensure_ascii=False)
        print(f"[OK] Appended latest merged JSON: {os.path.basename(latest_json)}")
    except Exception as e:
        print(f"[WARN] Failed to write destination JSON: {e}")

def run_pipeline():
    """Run the actuarial pipeline"""
    global final_path
    os.makedirs(CALC_DIR, exist_ok=True)
    os.makedirs(FINAL_DIR, exist_ok=True)

    input_path = os.path.join(CALC_DIR, "sample_input.json")
    facultative_path = os.path.join(CALC_DIR, "facultative_reinsurance_calculations.json")
    final_path = os.path.join(FINAL_DIR, "decisions.json")

    # 1. Step 1 - run enrichment (code.py)
    print("[PIPELINE] Running enrichment...")
    risks = code_module.load_input(input_path)
    enriched_records = [code_module.enrich_risk_record(r) for r in risks]
    code_module.write_output(facultative_path, enriched_records)

    # 2. Step 2 - run calculator (calculator.py)
    print("[PIPELINE] Running actuarial calculator...")
    df = calc_module.load_json_input(facultative_path)
    calculator = calc_module.FacultativeReinsuranceCalculator()
    df_calculated = calculator.calculate_all_metrics(df)
    calc_module.save_json_output(df_calculated, facultative_path)

    # 3. Step 3 - run decision engine (combine.py)
    print("[PIPELINE] Running decision engine...")
    with open(facultative_path, "r", encoding="utf-8") as f:
        calculated_data = json.load(f)
    decisions = decision_module.score_facultative_risks(calculated_data)

    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2)

    print("[OK] Pipeline finished successfully!")
    return final_path

def monitoring_loop():
    """Background monitoring loop"""
    global last_submission_count, last_extracted_count, final_path
    
    print("[MONITOR] Starting background monitoring...")
    
    # Initial counts
    last_submission_count = count_submission_folders()
    last_extracted_count = count_extracted_folders()
    
    print(f"[MONITOR] Current submissions: {last_submission_count}, extracted: {last_extracted_count}")
    
    # Run initial pipeline if we have data
    if last_submission_count > 0:
        print("[MONITOR] Running initial pipeline...")
        final_path = run_pipeline()
    
    # Main monitoring loop
    while True:
        try:
            # Check for new emails
            current_submissions = run_email_receiver()
            
            # If new submissions found, run extraction
            if current_submissions > last_submission_count:
                print(f"[EVENT] New submissions detected: {current_submissions - last_submission_count}")
                last_submission_count = current_submissions
                
                # Run extraction
                current_extracted = run_submission_extractor()
                
                # If new extractions, run NLP
                if current_extracted > last_extracted_count:
                    print(f"[EVENT] New extractions detected: {current_extracted - last_extracted_count}")
                    last_extracted_count = current_extracted
                    
                    # Run NLP processing
                    if run_nlp_processing():
                        # Append latest merged JSON and run pipeline
                        append_latest_merged_json()
                        final_path = run_pipeline()
                        print("[EVENT] Pipeline updated with new data")
            
            # Wait before next check
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            print(f"[ERROR] Monitoring error: {e}")
            time.sleep(60)  # Wait longer on error

def create_app():
    """Create Flask app"""
    app = Flask(__name__)

    if not os.path.isdir(FRONTEND_DIR):
        print(f"[WARN] Frontend directory not found: {FRONTEND_DIR}")

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*") or "*"
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

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

    @app.route("/")
    def serve_index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/detail.html")
    def serve_detail():
        return send_from_directory(FRONTEND_DIR, "detail.html")

    @app.route("/<path:path>")
    def serve_assets(path):
        return send_from_directory(FRONTEND_DIR, path)

    return app

if __name__ == "__main__":
    print("[STARTUP] Initializing system...")
    
    # Start monitoring in background thread
    monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitor_thread.start()
    
    # Create and run Flask app
    app = create_app()
    
    print("\n[WEB] Server starting at: http://127.0.0.1:5000")
    print(f"   Serving frontend from: {FRONTEND_DIR}")
    print("   API: /api/decisions")
    print("   Monitoring: Background thread (every 30s)")
    print("   Press Ctrl+C to stop")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server stopped by user")

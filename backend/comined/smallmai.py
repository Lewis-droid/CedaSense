import os
import sys
import json
import importlib.util

# Resolve backend root dynamically
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# Absolute paths to target scripts and files
PATH_TEST2 = os.path.join(BACKEND_ROOT, "email", "test2.py")
PATH_SUBMISSION_EXTRACTOR = os.path.join(BACKEND_ROOT, "email", "submission_extractor.py")
PATH_APITEST = os.path.join(BACKEND_ROOT, "nlp2", "APItest.py")

# Source JSON to append and destination sample_input.json
SRC_MERGED_JSON = os.path.join(
    BACKEND_ROOT,
    "email",
    "nlp2",
    "merged_json",
    "2025",
    "09_September",
    "Submission_20250925_204109_gichinga03_at_gmail.com.json",
)
DEST_SAMPLE_INPUT = os.path.join(BACKEND_ROOT, "calcultaions", "sample_input.json")


def load_module_from_path(module_name: str, file_path: str):
    """Dynamically load a module from an absolute file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_email_receiver():
    """Run the email receiver to fetch and save new submissions."""
    mod = load_module_from_path("email_processor", PATH_TEST2)
    if hasattr(mod, "process_emails"):
        print("📥 Running email receiver ...")
        mod.process_emails()
    else:
        print("⚠️ process_emails() not found in test2.py")


def run_submission_extractor():
    """Run the converter to extract text from submissions."""
    mod = load_module_from_path("submission_extractor", PATH_SUBMISSION_EXTRACTOR)
    if hasattr(mod, "process_all_existing_submissions"):
        print("🧾 Extracting text from submissions ...")
        mod.process_all_existing_submissions()
    else:
        print("⚠️ process_all_existing_submissions() not found in submission_extractor.py")


def run_nlp_processing():
    """Run the NLP processing to produce merged JSON outputs."""
    mod = load_module_from_path("apitest_runner", PATH_APITEST)
    if hasattr(mod, "process_all_submissions"):
        print("🧠 Running NLP processing on extracted text ...")
        mod.process_all_submissions()
    else:
        print("⚠️ process_all_submissions() not found in APItest.py")


def append_merged_json_to_sample_input(src_json_path: str, dest_sample_input_path: str):
    """Append a single merged JSON object into the sample_input.json array."""
    if not os.path.isfile(src_json_path):
        print(f"⚠️ Source JSON not found: {src_json_path}")
        return

    try:
        with open(src_json_path, "r", encoding="utf-8") as f:
            data_obj = json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to read source JSON: {e}")
        return

    # Ensure destination exists and is a list
    dest_data = []
    if os.path.isfile(dest_sample_input_path):
        try:
            with open(dest_sample_input_path, "r", encoding="utf-8") as f:
                dest_data = json.load(f)
            if not isinstance(dest_data, list):
                print("⚠️ Destination JSON is not a list. Aborting append.")
                return
        except Exception as e:
            print(f"⚠️ Failed to read destination JSON, starting new list: {e}")
            dest_data = []

    dest_data.append(data_obj)

    try:
        with open(dest_sample_input_path, "w", encoding="utf-8") as f:
            json.dump(dest_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Appended merged JSON into: {dest_sample_input_path}")
    except Exception as e:
        print(f"⚠️ Failed to write destination JSON: {e}")


if __name__ == "__main__":
    # 1) Receive new emails and save to submissions
    run_email_receiver()

    # 2) Extract text from supported attachments into extracted/ tree
    run_submission_extractor()

    # 3) NLP processing to produce merged JSONs per submission
    run_nlp_processing()

    # 4) Append specific merged JSON into sample_input.json
    append_merged_json_to_sample_input(SRC_MERGED_JSON, DEST_SAMPLE_INPUT) 
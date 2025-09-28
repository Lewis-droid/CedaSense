import imaplib
import email
from email.header import decode_header
from email import policy
import os
import datetime
import logging
import sys

# ======================= CONFIGURATION =======================
IMAP_SERVER = "imap.gmail.com"  # or "outlook.office365.com"

# Hardcoded email credentials
EMAIL_USER = "cedasense@gmail.com"
EMAIL_PASS = "xnuh vvno rvgq jiaz"

SENDER_WHITELIST = set()  # Empty set accepts all senders
BASE_FOLDER = os.path.join(os.getcwd(), "Facultative_Submissions")
SUBJECT_KEYWORD = "Facultative Submission"
MIN_ATTACHMENTS = 1

# Allowed attachment file types
ALLOWED_EXTENSIONS = {
    ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv",
    ".msg", ".xml", ".json", ".png", ".jpg", ".jpeg",
    ".tif", ".pdf", ".rar", ".zip"
}

# Logging setup
logging.basicConfig(filename="facultative_log.txt",
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
# =============================================================

# ---------------- Helper Functions ----------------

def decode_filename(filename):
    if filename:
        decoded, charset = decode_header(filename)[0]
        if isinstance(decoded, bytes):
            return decoded.decode(charset or "utf-8", errors="ignore")
        return decoded
    return "unknown_file"

def create_submission_folder(sender_email):
    safe_email = (sender_email.replace("@", "_at_")
                              .replace(":", "_")
                              .replace("/", "_")
                              .replace("\\", "_"))
    now = datetime.datetime.now()
    year_folder = os.path.join(BASE_FOLDER, str(now.year))
    month_folder = os.path.join(year_folder, f"{now.month:02d}_{now.strftime('%B')}")
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    submission_folder = os.path.join(month_folder, f"Submission_{timestamp}_{safe_email}")
    os.makedirs(submission_folder, exist_ok=True)
    return submission_folder

def save_email_content(msg, folder):
    """Save email body only in plain text (skip HTML)."""
    for part in msg.walk():
        disposition = part.get_content_disposition()
        content_type = part.get_content_type()
        if disposition != "attachment":
            try:
                if content_type == "text/plain":
                    with open(os.path.join(folder, "email_body.txt"), "w", encoding="utf-8") as f:
                        f.write(part.get_content())
            except Exception as e:
                logging.warning(f"Failed to save email body: {e}")

def save_attachments(msg, folder):
    """Save all attachments filtered by allowed extensions."""
    for part in msg.walk():
        filename = decode_filename(part.get_filename())
        if filename:
            ext = os.path.splitext(filename)[1].lower()
            if ext in ALLOWED_EXTENSIONS:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        filepath = os.path.join(folder, filename)
                        with open(filepath, "wb") as f_attach:
                            f_attach.write(payload)
                        logging.info(f"Saved attachment: {filename}")
                except Exception as e:
                    logging.warning(f"Failed to save attachment {filename}: {e}")
            else:
                logging.info(f"Skipped unsupported attachment type: {filename}")

# ---------------- Main Processing Function ----------------

def process_emails():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)

    # Login with error handling
    try:
        mail.login(EMAIL_USER, EMAIL_PASS)
    except imaplib.IMAP4.error as e:
        print("❌ IMAP login failed. Check your credentials or app password.")
        logging.error(f"IMAP login failed: {e}")
        mail.logout()
        sys.exit(1)

    mail.select("inbox")

    # Search for unread emails matching subject
    status, data = mail.search(None, f'(UNSEEN SUBJECT "{SUBJECT_KEYWORD}")')
    email_ids = data[0].split()
    print(f"Found {len(email_ids)} candidate emails")

    for eid in email_ids:
        try:
            status, msg_data = mail.fetch(eid, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email, policy=policy.default)

            # Decode subject
            subject, enc = decode_header(msg.get("Subject"))[0]
            if isinstance(subject, bytes):
                subject = subject.decode(enc or "utf-8", errors="ignore")

            # Extract sender
            from_addr = email.utils.parseaddr(msg.get("From"))[1].lower()

            # Count attachments
            attachment_count = sum(
                1 for part in msg.walk() if part.get_filename() is not None
            )

            if attachment_count >= MIN_ATTACHMENTS and (not SENDER_WHITELIST or from_addr in SENDER_WHITELIST):
                submission_folder = create_submission_folder(from_addr)

                # Save email body (plain text only)
                save_email_content(msg, submission_folder)

                # Save attachments (robust)
                save_attachments(msg, submission_folder)

                # Mark email as read
                mail.store(eid, '+FLAGS', '\\Seen')

                print(f"✅ Processed email from {from_addr} | Subject: {subject}")
                logging.info(f"Processed email from {from_addr} | Subject: {subject} | Attachments: {attachment_count}")
            else:
                print(f"❌ Skipped email from {from_addr} | Subject: {subject}")
                logging.info(f"Skipped email from {from_addr} | Subject: {subject} | Attachments: {attachment_count}")

        except Exception as e:
            print(f"⚠️ Error processing email ID {eid}: {e}")
            logging.error(f"Error processing email ID {eid}: {e}")

    mail.logout()

# ---------------- Entry Point ----------------

if __name__ == "__main__":
    os.makedirs(BASE_FOLDER, exist_ok=True)
    process_emails()

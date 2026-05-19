"""
email_handler/gmail_sender.py
------------------------------
Gmail Integration (smtplib + App Password Auth)

Handles:
  - Connecting to Gmail's SMTP server securely (TLS)
  - Authenticating with a Gmail App Password
  - Attaching the encrypted file to an email
  - Sending the email to a recipient

IMPORTANT — Gmail Setup Required:
  Gmail no longer allows plain password login.
  You must use a Gmail App Password:
    1. Go to your Google Account → Security
    2. Enable 2-Step Verification (if not already)
    3. Go to Security → App Passwords
    4. Create a new app password (select "Mail" + "Windows Computer" or "Other")
    5. Copy the 16-character password — use that as your password here.
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders

# --- Gmail SMTP Settings ---
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587          # TLS port (STARTTLS)



# CONNECTION & AUTHENTICATION


def create_smtp_connection(sender_email: str, app_password: str) -> smtplib.SMTP:
    server = smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT)
    server.ehlo()                 # Identify to the server
    server.starttls()             # Upgrade connection to TLS
    server.ehlo()                 # Re-identify after TLS
    server.login(sender_email, app_password)
    return server


def test_connection(sender_email: str, app_password: str) -> tuple[bool, str]:
    try:
        server = create_smtp_connection(sender_email, app_password)
        server.quit()
        return True, "Connected successfully to Gmail."
    except smtplib.SMTPAuthenticationError:
        return False, (
            "Authentication failed. Check your email and App Password.\n"
            "Remember: use a Gmail App Password, not your regular password."
        )
    except Exception as e:
        return False, f"Connection error: {str(e)}"



# EMAIL COMPOSITION


def build_email(
    sender_email: str,
    recipient_email: str,
    subject: str,
    body: str,
    attachment_path: str,
) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"]    = sender_email
    msg["To"]      = recipient_email
    msg["Subject"] = subject

    # Attach the plain-text body
    msg.attach(MIMEText(body, "plain"))

    # Attach the encrypted file
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            payload = f.read()

        part = MIMEBase("application", "octet-stream")
        part.set_payload(payload)
        encoders.encode_base64(part)

        filename = os.path.basename(attachment_path)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)

    return msg


def build_default_email_body(original_filename: str, sender_name: str = "") -> str:
    name_line = f"Sent by: {sender_name}\n\n" if sender_name else ""
    return (
        f"Hello,\n\n"
        f"Please find the attached encrypted file: {original_filename}.enc\n\n"
        f"{name_line}"
        f"This file has been encrypted using AES-256-GCM encryption.\n"
        f"You will need the shared private key and the decryption program to open it.\n\n"
        f"Do not share the key over this email — use a separate secure channel.\n\n"
        f"Best regards"
    )



# SENDING


def send_encrypted_file(
    sender_email: str,
    app_password: str,
    recipient_email: str,
    attachment_path: str,
    subject: str = None,
    body: str = None,
    sender_name: str = "",
) -> tuple[bool, str]:
    # Validate attachment exists
    if not os.path.exists(attachment_path):
        return False, f"Attachment not found: {attachment_path}"

    # Build subject/body defaults
    original_filename = os.path.basename(attachment_path).replace(".enc", "")
    if subject is None:
        subject = f"Encrypted File: {original_filename}"
    if body is None:
        body = build_default_email_body(original_filename, sender_name)

    try:
        # Build the email message
        msg = build_email(
            sender_email    = sender_email,
            recipient_email = recipient_email,
            subject         = subject,
            body            = body,
            attachment_path = attachment_path,
        )

        # Connect and send
        server = create_smtp_connection(sender_email, app_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()

        return True, f"Email sent successfully to {recipient_email}!"

    except smtplib.SMTPAuthenticationError:
        return False, (
            "Gmail authentication failed.\n"
            "Make sure you are using a Gmail App Password, not your regular password.\n"
            "Go to: Google Account → Security → App Passwords"
        )
    except smtplib.SMTPRecipientsRefused:
        return False, f"Recipient address rejected: {recipient_email}"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"



def validate_email_address(email: str) -> tuple[bool, str]:
    import re
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, email.strip()):
        return True, "OK"
    return False, f"'{email}' does not look like a valid email address."


def validate_app_password(app_password: str) -> tuple[bool, str]:
    stripped = app_password.replace(" ", "")
    if len(stripped) == 16 and stripped.isalpha():
        return True, "OK"
    return False, (
        "Gmail App Passwords are 16 letters (e.g. 'abcd efgh ijkl mnop').\n"
        "Check Google Account → Security → App Passwords."
    )

import os
import sys
import json
import traceback
import urllib.request
import urllib.parse
from config import LOGGING_BOT_TOKEN, ADMIN_CHAT_ID

def send_telegram_message(text: str):
    """Sends a text message to the admin chat using the logging bot token."""
    if not LOGGING_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("Telegram logging configurations are missing. Skipping notification.")
        return False
    
    url = f"https://api.telegram.org/bot{LOGGING_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    headers = {"Content-Type": "application/json"}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except Exception as e:
        print(f"Failed to send logging message to Telegram: {e}")
        return False

def send_telegram_document(file_path: str, caption: str):
    """Sends a local file as a Telegram document using multipart/form-data (built-in urllib)."""
    if not LOGGING_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("Telegram logging configurations are missing. Skipping document upload.")
        return False
    
    url = f"https://api.telegram.org/bot{LOGGING_BOT_TOKEN}/sendDocument"
    boundary = "---ArqiveResellerBoundary---"
    
    # Read file content
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
    except Exception as e:
        print(f"Failed to read file {file_path} for upload: {e}")
        return False

    # Build multipart payload
    filename = os.path.basename(file_path)
    body = []
    
    # Add chat_id field
    body.append(f"--{boundary}".encode("utf-8"))
    body.append(f'Content-Disposition: form-data; name="chat_id"'.encode("utf-8"))
    body.append(b"")
    body.append(str(ADMIN_CHAT_ID).encode("utf-8"))
    
    # Add caption field
    body.append(f"--{boundary}".encode("utf-8"))
    body.append(f'Content-Disposition: form-data; name="caption"'.encode("utf-8"))
    body.append(b"")
    body.append(caption.encode("utf-8"))
    
    # Add file field
    body.append(f"--{boundary}".encode("utf-8"))
    body.append(f'Content-Disposition: form-data; name="document"; filename="{filename}"'.encode("utf-8"))
    body.append(b"Content-Type: text/plain")
    body.append(b"")
    body.append(file_data)
    
    # End multipart
    body.append(f"--{boundary}--".encode("utf-8"))
    body.append(b"")
    
    payload_data = b"\r\n".join(body)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(payload_data))
    }
    
    try:
        req = urllib.request.Request(url, data=payload_data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status == 200
    except Exception as e:
        print(f"Failed to send logging document to Telegram: {e}")
        return False

def send_log(message: str):
    """Sends a general log notification to the admin chat."""
    print(f"Logging notification: {message}")
    send_telegram_message(f"ℹ️ **Arqive Reseller Log:**\n{message}")

def send_error(exception: Exception, context: str = ""):
    """Captures the traceback, formats a clean Markdown error message, and uploads it."""
    err_type = type(exception).__name__
    err_msg = str(exception)
    tb_str = traceback.format_exc()
    
    print(f"Error captured in {context}: {err_type}: {err_msg}", file=sys.stderr)
    print(tb_str, file=sys.stderr)
    
    summary = f"⚠️ **CRITICAL ERROR** in Arqive Reseller Pipeline\n"
    if context:
        summary += f"**Context**: {context}\n"
    summary += f"**Exception**: `{err_type}`\n"
    summary += f"**Details**: {err_msg}"
    
    # If the traceback is small enough, send it in a code block directly
    full_message = f"{summary}\n\n```python\n{tb_str}\n```"
    if len(full_message) <= 4000:
        return send_telegram_message(full_message)
    else:
        # Otherwise, send the summary message and attach the traceback as a file
        send_telegram_message(summary)
        
        temp_log = "traceback_error.txt"
        try:
            with open(temp_log, "w", encoding="utf-8") as f:
                f.write(tb_str)
            
            success = send_telegram_document(temp_log, f"Traceback log for error: {err_type}")
            return success
        finally:
            if os.path.exists(temp_log):
                try:
                    os.remove(temp_log)
                except Exception:
                    pass

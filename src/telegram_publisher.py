import os
import json
import urllib.request
import urllib.parse
from typing import Optional, List

LOCAL_BOT_API_URL = "http://localhost:8081"
PUBLIC_BOT_API_URL = "https://api.telegram.org"

def get_bot_username(token: str) -> str:
    """Retrieves the bot's username using getMe."""
    url = f"{PUBLIC_BOT_API_URL}/bot{token}/getMe"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            if data.get("ok"):
                return data["result"]["username"]
    except Exception as e:
        print(f"Failed to get bot username: {e}")
    return "ArqiveBot"

def upload_document_local(token: str, chat_id: str, file_path: str, caption: str = "", thread_id: Optional[int] = None) -> Optional[str]:
    """
    Uploads a document (up to 2GB) to the local Telegram Bot API server.
    Returns the uploaded file_id on success.
    """
    if not os.path.exists(file_path):
        print(f"Local file {file_path} not found for Telegram upload.")
        return None
        
    file_size = os.path.getsize(file_path)
    print(f"Uploading file {os.path.basename(file_path)} ({file_size / 1024 / 1024:.2f}MB) via Local Bot API server...")
    
    url = f"{LOCAL_BOT_API_URL}/bot{token}/sendDocument"
    boundary = "---ArqiveTelegramPublisherBoundary---"
    
    # Read file data
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
    except Exception as e:
        print(f"Failed to read file for local Telegram upload: {e}")
        return None

    # Construct multipart request
    body = []
    
    # Add chat_id
    body.append(f"--{boundary}".encode("utf-8"))
    body.append(f'Content-Disposition: form-data; name="chat_id"'.encode("utf-8"))
    body.append(b"")
    body.append(str(chat_id).encode("utf-8"))
    
    # Add caption
    body.append(f"--{boundary}".encode("utf-8"))
    body.append(f'Content-Disposition: form-data; name="caption"'.encode("utf-8"))
    body.append(b"")
    body.append(caption.encode("utf-8"))
    
    # Add parse_mode
    body.append(f"--{boundary}".encode("utf-8"))
    body.append(f'Content-Disposition: form-data; name="parse_mode"'.encode("utf-8"))
    body.append(b"")
    body.append(b"Markdown")
    
    # Add message_thread_id if provided
    if thread_id:
        body.append(f"--{boundary}".encode("utf-8"))
        body.append(f'Content-Disposition: form-data; name="message_thread_id"'.encode("utf-8"))
        body.append(b"")
        body.append(str(thread_id).encode("utf-8"))
        
    # Add document file
    filename = os.path.basename(file_path)
    body.append(f"--{boundary}".encode("utf-8"))
    body.append(f'Content-Disposition: form-data; name="document"; filename="{filename}"'.encode("utf-8"))
    body.append(b"Content-Type: application/zip")
    body.append(b"")
    body.append(file_data)
    
    body.append(f"--{boundary}--".encode("utf-8"))
    body.append(b"")
    
    payload = b"\r\n".join(body)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(payload))
    }
    
    try:
        # We increase the timeout dramatically for large files
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=300) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("ok"):
                file_id = res_data["result"]["document"]["file_id"]
                print(f"Uploaded successfully to Telegram! File ID: {file_id}")
                return file_id
            else:
                print(f"Telegram local upload failed: {res_data}")
    except Exception as e:
        print(f"Error during Telegram local upload: {e}")
        
    return None

def publish_invoice(token: str, chat_id: str, bot_username: str, file_id: str, title: str, description: str, price_stars: int, thread_id: Optional[int] = None) -> Optional[int]:
    """
    Sends a native Stars invoice to the storefront channel.
    Returns the message_id on success.
    """
    url = f"{PUBLIC_BOT_API_URL}/bot{token}/sendInvoice"
    
    # Construct inline keyboard with Pay and Subscription buttons
    # Note: Telegram requires the first button to be the Pay button
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": f"💳 Pay {price_stars} Stars ⭐️", "pay": True},
                {"text": "📥 Download via Subscription", "url": f"https://t.me/{bot_username}?start=sub_{file_id}"}
            ]
        ]
    }
    
    payload = {
        "chat_id": chat_id,
        "title": title[:32],  # Telegram limit is 32 chars
        "description": description[:250],  # Telegram limit is 250 chars
        "payload": f"pay_{file_id}",  # Identifying payload for payment
        "provider_token": "",  # Empty for Telegram Stars
        "currency": "XTR",  # Telegram Stars
        "prices": [{"label": "Stars Price", "amount": price_stars}],
        "reply_markup": reply_markup
    }
    
    if thread_id:
        payload["message_thread_id"] = thread_id
        
    headers = {"Content-Type": "application/json"}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            if res_data.get("ok"):
                message_id = res_data["result"]["message_id"]
                print(f"Stars invoice posted successfully to chat {chat_id}! Msg ID: {message_id}")
                return message_id
    except Exception as e:
        print(f"Failed to publish Stars invoice to Telegram: {e}")
    return None

def publish_free_doc(token: str, chat_id: str, file_id: str, caption: str, thread_id: Optional[int] = None) -> Optional[int]:
    """Posts a raw ZIP file (by cached file_id) to the target channel."""
    url = f"{PUBLIC_BOT_API_URL}/bot{token}/sendDocument"
    payload = {
        "chat_id": chat_id,
        "document": file_id,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    
    if thread_id:
        payload["message_thread_id"] = thread_id
        
    headers = {"Content-Type": "application/json"}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            if res_data.get("ok"):
                message_id = res_data["result"]["message_id"]
                print(f"Free document document posted successfully! Msg ID: {message_id}")
                return message_id
    except Exception as e:
        print(f"Failed to post free document: {e}")
    return None

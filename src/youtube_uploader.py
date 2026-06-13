import os
import json
import urllib.request
import urllib.parse
from typing import List, Optional
from config import YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN, OPENROUTER_API_KEY, OPENROUTER_URL

def get_access_token() -> str:
    """Uses the OAuth2 refresh token to retrieve a fresh access token from Google."""
    if not YOUTUBE_CLIENT_ID or not YOUTUBE_CLIENT_SECRET or not YOUTUBE_REFRESH_TOKEN:
        raise ValueError("YouTube OAuth2 credentials (Client ID, Secret, or Refresh Token) are missing.")
        
    url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "refresh_token": YOUTUBE_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return res_data["access_token"]
    except Exception as e:
        print(f"Failed to refresh YouTube access token: {e}")
        raise

def generate_tags_with_deepseek(pack_name: str, genre: str) -> List[str]:
    """Queries OpenRouter DeepSeek to generate optimized tag lists. Fallback to defaults."""
    default_tags = ["drumkit", "sample pack", "music producer", "type beat", genre.lower()]
    if not OPENROUTER_API_KEY:
        return default_tags
        
    url = f"{OPENROUTER_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/arqive-developer/drumkit-reseller",
    }
    
    prompt = (
        f"Generate 10 highly optimized, comma-separated SEO tags for a YouTube video showcasing a rebranded "
        f"drum kit named '{pack_name}' in the music genre '{genre}'. "
        f"Output ONLY the comma-separated list of tags, nothing else."
    )
    
    payload = {
        "model": "deepseek/deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"].strip()
            tags = [t.strip() for t in content.split(",") if t.strip()]
            return tags[:15] if tags else default_tags
    except Exception as e:
        print(f"DeepSeek tag generation failed, using defaults: {e}")
        return default_tags

def upload_video(file_path: str, title: str, description: str, tags: List[str], access_token: str) -> Optional[str]:
    """
    Performs a native resumable upload of the video to YouTube.
    Returns the video ID on success.
    """
    if not os.path.exists(file_path):
        print(f"Video file {file_path} does not exist.")
        return None
        
    file_size = os.path.getsize(file_path)
    
    # 1. Initiate Resumable Session
    init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/*",
        "X-Upload-Content-Length": str(file_size)
    }
    
    metadata = {
        "snippet": {
            "title": title[:100],  # YouTube title limit
            "description": description,
            "tags": tags,
            "categoryId": "10"  # Music category ID
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }
    
    try:
        req_init = urllib.request.Request(init_url, data=json.dumps(metadata).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req_init, timeout=20) as response:
            upload_session_url = response.headers.get("Location")
    except Exception as e:
        print(f"Failed to initiate YouTube upload session: {e}")
        return None
        
    if not upload_session_url:
        print("Upload session URL was not returned in Location header.")
        return None

    # 2. Upload video bytes to the session URL
    print(f"Uploading video bytes ({file_size / 1024 / 1024:.2f}MB) to YouTube...")
    try:
        # We read the file in chunks or raw bytes (resumable PUT)
        with open(file_path, "rb") as f:
            video_data = f.read()
            
        req_upload = urllib.request.Request(
            upload_session_url, 
            data=video_data, 
            headers={"Content-Type": "video/*", "Content-Length": str(file_size)}, 
            method="PUT"
        )
        
        with urllib.request.urlopen(req_upload, timeout=120) as response:
            if response.status in (200, 201):
                res_data = json.loads(response.read().decode("utf-8"))
                video_id = res_data.get("id")
                print(f"YouTube upload successful! Video ID: {video_id}")
                return video_id
    except Exception as e:
        print(f"Failed to upload video bytes to YouTube: {e}")
        
    return None

def add_comment_to_video(video_id: str, comment_text: str, access_token: str) -> bool:
    """Adds a top-level comment to the uploaded YouTube video."""
    url = "https://www.googleapis.com/youtube/v3/commentThreads?part=snippet"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {
                    "textOriginal": comment_text
                }
            }
        }
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.status == 200
    except Exception as e:
        print(f"Failed to add pinned/top comment to YouTube video: {e}")
        return False

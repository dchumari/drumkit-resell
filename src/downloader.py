import os
import re
import urllib.request
import urllib.parse
import subprocess
import shutil
from typing import Tuple, Optional

# Supported URL regexes
DRIVE_RE = re.compile(r"drive\.google\.com/(?:file/d/|drive/folders/|open\?id=)([a-zA-Z0-9_-]+)")
MEDIAFIRE_RE = re.compile(r"mediafire\.com/(?:file/|folder/|download/|/?\?)([a-zA-Z0-9_-]+)")
MEGA_RE = re.compile(r"mega\.nz/(?:#\!|file/|folder/)([a-zA-Z0-9_-]+)")

def get_link_type(url: str) -> str:
    """Identifies the file sharing host."""
    if DRIVE_RE.search(url):
        return "gdrive"
    elif MEDIAFIRE_RE.search(url):
        return "mediafire"
    elif MEGA_RE.search(url):
        return "mega"
    return "unsupported"

def check_mediafire_link(url: str) -> Tuple[bool, int, Optional[str]]:
    """Checks Mediafire link availability, file size, and extracts the direct download URL."""
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")
            
        # Regex to find direct download link
        direct_link_match = re.search(r'href="(https://download\d+\.mediafire\.com/[^"]+)"', html)
        if not direct_link_match:
            # Fallback regex
            direct_link_match = re.search(r'(https://download\d+\.mediafire\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9._-]+)', html)
            
        if not direct_link_match:
            return False, 0, None
            
        direct_url = direct_link_match.group(1)
        
        # Check size using a HEAD request on the direct link
        req_head = urllib.request.Request(direct_url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_head, timeout=10) as head_response:
            size = int(head_response.headers.get("Content-Length", 0))
            
        return True, size, direct_url
    except Exception as e:
        print(f"Error checking Mediafire link: {e}")
        return False, 0, None

def check_gdrive_link(url: str) -> Tuple[bool, int, str]:
    """Checks Google Drive link accessibility and size without downloading."""
    match = DRIVE_RE.search(url)
    if not match:
        return False, 0, "invalid"
        
    id_ = match.group(1)
    is_folder = "folders" in url
    
    if is_folder:
        # For folders, we check access by querying the folder page
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as res:
                html = res.read().decode("utf-8", errors="ignore")
            if "Google Drive" in html and "folders" in url:
                return True, 50000000, "folder"  # Assume size is large enough (>50MB)
        except Exception:
            return False, 0, "invalid"
            
    # For files, query Google's direct link
    direct_url = f"https://drive.google.com/uc?export=download&id={id_}"
    try:
        req = urllib.request.Request(direct_url, method="GET", headers={"User-Agent": "Mozilla/5.0"})
        # We only read the headers
        with urllib.request.urlopen(req, timeout=15) as response:
            size = int(response.headers.get("Content-Length", 0))
            # If Google serves a confirmation/warning page (quota exceeded), content-type is text/html
            content_type = response.headers.get("Content-Type", "")
            
            if "text/html" in content_type and size < 50000:
                # Likely quota warning page
                html = response.read(10000).decode("utf-8", errors="ignore")
                if "quota" in html.lower() or "exceeded" in html.lower() or "too many users" in html.lower():
                    return True, 0, "quota_exceeded"
                return False, 0, "invalid"
                
            return True, size, "file"
    except Exception as e:
        print(f"Error checking GDrive file: {e}")
        return False, 0, "invalid"

def check_mega_link(url: str) -> Tuple[bool, int]:
    """Checks Mega link availability. Requires mega.py or megacmd. Falls back to CLI check."""
    # Since checking mega links metadata via raw urllib is complex, we check using a subprocess check
    # or assume it is valid if the page resolves.
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                # We assume it's valid. Mega links are handled via CLI/libraries later.
                return True, 50000000  # Default to >50MB
    except Exception:
        pass
    return False, 0

def check_link(url: str) -> Tuple[bool, str, int]:
    """
    Checks if link is online, active, and has downloadable content > 5MB.
    Returns (is_valid, link_type, size_bytes).
    """
    ltype = get_link_type(url)
    if ltype == "unsupported":
        return False, "unsupported", 0
        
    if ltype == "mediafire":
        ok, size, _ = check_mediafire_link(url)
        if ok and size < 5 * 1024 * 1024:
            print(f"Mediafire link is too small ({size / 1024 / 1024:.2f}MB). Skipping.")
            return False, "mediafire", size
        return ok, "mediafire", size
        
    elif ltype == "gdrive":
        ok, size, status = check_gdrive_link(url)
        if status == "quota_exceeded":
            return True, "gdrive_quota", 0
        if ok and size < 5 * 1024 * 1024 and status == "file":
            print(f"Google Drive link is too small ({size / 1024 / 1024:.2f}MB). Skipping.")
            return False, "gdrive", size
        return ok, "gdrive", size
        
    elif ltype == "mega":
        ok, size = check_mega_link(url)
        return ok, "mega", size
        
    return False, "unsupported", 0

def download_file(url: str, output_path: str) -> bool:
    """
    Downloads the file from the given URL to output_path.
    Creates parent directories if necessary.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    ltype = get_link_type(url)
    
    if ltype == "mediafire":
        ok, _, direct_url = check_mediafire_link(url)
        if not ok or not direct_url:
            print("Failed to resolve Mediafire direct URL.")
            return False
        try:
            print(f"Downloading from Mediafire: {direct_url}")
            req = urllib.request.Request(direct_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response, open(output_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)
            return True
        except Exception as e:
            print(f"Error downloading Mediafire: {e}")
            return False
            
    elif ltype == "gdrive":
        try:
            import gdown
            print(f"Downloading from Google Drive via gdown: {url}")
            # If it is a folder, use gdown's download_folder
            is_folder = "folders" in url
            try:
                if is_folder:
                    res = gdown.download_folder(url, output=output_path, quiet=False, use_cookies=False)
                    return res is not None
                else:
                    res = gdown.download(url, output=output_path, quiet=False)
                    return res is not None
            except Exception as err:
                print(f"gdown library download failed with error: {err}")
                return False
        except ImportError:
            # Fallback to CLI
            print("gdown python library not found. Falling back to CLI.")
            is_folder = "folders" in url
            cmd = ["gdown"]
            if is_folder:
                cmd.append("--folder")
            cmd.extend([url, "-o", output_path, "--fuzzy"])
            try:
                res = subprocess.run(cmd, check=True)
                return res.returncode == 0
            except Exception as e:
                print(f"Error downloading Google Drive CLI: {e}")
                return False
                
    elif ltype == "mega":
        # We can download Mega files using megacmd or the python mega library.
        # Below is a subprocess wrapper that checks for mega-get command or uses mega-dl.
        # Alternatively, we can use a python mega wrapper.
        try:
            from mega import Mega
            print(f"Downloading from Mega via mega.py: {url}")
            mega = Mega()
            m = mega.login()
            m.download_url(url, dest_path=os.path.dirname(output_path), dest_filename=os.path.basename(output_path))
            return os.path.exists(output_path)
        except Exception as e:
            print(f"mega.py download failed: {e}. Trying megacmd fallback.")
            # Fallback to megacmd if installed
            # command: mega-get <link> <dest>
            cmd = ["mega-get", url, output_path]
            try:
                res = subprocess.run(cmd, check=True)
                return res.returncode == 0
            except Exception as e2:
                print(f"megacmd download failed: {e2}")
                # Try raw curl megadl wrapper if available
                return False
                
    return False

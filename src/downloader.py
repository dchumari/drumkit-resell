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
            # 1. Translate URL from modern format to legacy format
            translated_url = url
            if "file/" in url and "#" in url:
                parts = url.split("file/")
                subparts = parts[1].split("#")
                translated_url = f"{parts[0]}#!{subparts[0]}!{subparts[1]}"
                print(f"Translated Mega URL for legacy library parser: {translated_url}")

            # 2. Apply monkeypatch to mega library dynamically to make it bytes-safe on Python 3
            import mega
            from Crypto.Cipher import AES
            from Crypto.Util import Counter
            import requests
            import tempfile

            # Monkeypatch AES.new if not already patched
            if not getattr(AES, "_patched_for_mega", False):
                original_aes_new = AES.new

                def patched_aes_new(key, *args, **kwargs):
                    if isinstance(key, str):
                        key = key.encode("utf-8")
                    args_list = list(args)
                    if len(args_list) >= 2 and isinstance(args_list[1], str):
                        args_list[1] = args_list[1].encode("utf-8")
                    iv_val = kwargs.get("IV") or kwargs.get("iv")
                    if iv_val and isinstance(iv_val, str):
                        if "IV" in kwargs:
                            kwargs["IV"] = iv_val.encode("utf-8")
                        if "iv" in kwargs:
                            kwargs["iv"] = iv_val.encode("utf-8")
                    return original_aes_new(key, *args_list, **kwargs)

                AES.new = patched_aes_new
                AES._patched_for_mega = True

            # Monkeypatch mega.Mega._download_file if not already patched
            if not getattr(mega.Mega, "_patched_for_py3", False):
                def patched_download_file(
                    self,
                    file_handle,
                    file_key,
                    dest_path=None,
                    dest_filename=None,
                    is_public=False,
                    file=None
                ):
                    from mega.crypto import (
                        base64_to_a32, base64_url_decode, decrypt_attr, a32_to_str,
                        get_chunks, str_to_a32
                    )
                    from mega.errors import RequestError
                    
                    if file is None:
                        if is_public:
                            file_key = base64_to_a32(file_key)
                            file_data = self._api_request({'a': 'g', 'g': 1, 'p': file_handle})
                        else:
                            file_data = self._api_request({'a': 'g', 'g': 1, 'n': file_handle})

                        k = (
                            file_key[0] ^ file_key[4], file_key[1] ^ file_key[5],
                            file_key[2] ^ file_key[6], file_key[3] ^ file_key[7]
                        )
                        iv = file_key[4:6] + (0, 0)
                        meta_mac = file_key[6:8]
                    else:
                        file_data = self._api_request({'a': 'g', 'g': 1, 'n': file['h']})
                        k = file['k']
                        iv = file['iv']
                        meta_mac = file['meta_mac']

                    if 'g' not in file_data:
                        raise RequestError('File not accessible anymore')
                    file_url = file_data['g']
                    file_size = file_data['s']
                    attribs = base64_url_decode(file_data['at'])
                    attribs = decrypt_attr(attribs, k)

                    if dest_filename is not None:
                        file_name = dest_filename
                    else:
                        file_name = attribs['n']

                    input_file = requests.get(file_url, stream=True).raw

                    if dest_path is None:
                        dest_path = ''
                    else:
                        dest_path += '/'

                    temp_output_file = tempfile.NamedTemporaryFile(
                        mode='w+b', prefix='megapy_', delete=False
                    )

                    k_str = a32_to_str(k)
                    counter = Counter.new(128, initial_value=((iv[0] << 32) + iv[1]) << 64)
                    aes = AES.new(k_str, AES.MODE_CTR, counter=counter)

                    mac_str = b'\0' * 16
                    mac_encryptor = AES.new(k_str, AES.MODE_CBC, mac_str)
                    iv_str = a32_to_str([iv[0], iv[1], iv[0], iv[1]])

                    for chunk_start, chunk_size in get_chunks(file_size):
                        chunk = input_file.read(chunk_size)
                        chunk = aes.decrypt(chunk)
                        temp_output_file.write(chunk)

                        encryptor = AES.new(k_str, AES.MODE_CBC, iv_str)
                        for i in range(0, len(chunk) - 16, 16):
                            block = chunk[i:i + 16]
                            encryptor.encrypt(block)

                        if file_size > 16:
                            i += 16
                        else:
                            i = 0

                        block = chunk[i:i + 16]
                        if len(block) % 16:
                            block += b'\0' * (16 - (len(block) % 16))
                        mac_str = mac_encryptor.encrypt(encryptor.encrypt(block))

                    file_mac = str_to_a32(mac_str)
                    temp_output_file.close()

                    if (file_mac[0] ^ file_mac[1], file_mac[2] ^ file_mac[3]) != meta_mac:
                        raise ValueError('Mismatched mac')

                    shutil.move(temp_output_file.name, dest_path + file_name)

                mega.Mega._download_file = patched_download_file
                mega.Mega._patched_for_py3 = True

            print(f"Downloading from Mega via patched mega.py: {translated_url}")
            m = mega.Mega().login()
            m.download_url(translated_url, dest_path=os.path.dirname(output_path), dest_filename=os.path.basename(output_path))
            return os.path.exists(output_path)
        except Exception as e:
            print(f"mega.py download failed: {e}. Trying megacmd fallback.")
            # Fallback to megacmd if installed
            cmd = ["mega-get", url, output_path]
            try:
                res = subprocess.run(cmd, check=True)
                return res.returncode == 0
            except Exception as e2:
                print(f"megacmd download failed: {e2}")
                return False
                
    return False

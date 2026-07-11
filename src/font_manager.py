import os
import urllib.request
from PIL import ImageFont

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")

FONT_URLS = {
    "Mulish-Regular": "https://github.com/google/fonts/raw/main/ofl/mulish/static/Mulish-Regular.ttf",
    "Mulish-Bold": "https://github.com/google/fonts/raw/main/ofl/mulish/static/Mulish-Bold.ttf",
    "Nunito-Regular": "https://github.com/google/fonts/raw/main/ofl/nunito/static/Nunito-Regular.ttf",
    "Nunito-Bold": "https://github.com/google/fonts/raw/main/ofl/nunito/static/Nunito-Bold.ttf",
}

def get_local_font_path(font_family: str, suffix: str) -> str:
    """Resolves the path to a locally extracted font file in the assets/fonts/ subfolders, handling case/naming deviations."""
    variations = [font_family, font_family.replace("_", ""), font_family.replace(" ", "")]
    # Ensure unique values in variations list
    variations = list(dict.fromkeys(variations))
    
    for folder in variations:
        for file_prefix in variations:
            # 1. Check in static subfolder (e.g. assets/fonts/Open_Sans/static/OpenSans-Regular.ttf)
            path1 = os.path.join(FONTS_DIR, folder, "static", f"{file_prefix}-{suffix}.ttf")
            if os.path.exists(path1):
                return path1
            # 2. Check in main family subfolder (e.g. assets/fonts/Open_Sans/OpenSans-Regular.ttf)
            path2 = os.path.join(FONTS_DIR, folder, f"{file_prefix}-{suffix}.ttf")
            if os.path.exists(path2):
                return path2
            # 3. Check directly in fonts root folder (e.g. assets/fonts/OpenSans-Regular.ttf)
            path3 = os.path.join(FONTS_DIR, f"{file_prefix}-{suffix}.ttf")
            if os.path.exists(path3):
                return path3
    return ""


def ensure_font_downloaded(font_key: str) -> str:
    """Ensures a font file is present in assets/fonts/ directory by downloading it if necessary."""
    os.makedirs(FONTS_DIR, exist_ok=True)
    local_path = os.path.join(FONTS_DIR, f"{font_key}.ttf")
    
    if os.path.exists(local_path):
        return local_path
        
    url = FONT_URLS.get(font_key)
    if not url:
        return ""
        
    try:
        print(f"Downloading font {font_key} from {url}...")
        # Add User-Agent header to avoid blocking
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            with open(local_path, "wb") as f:
                f.write(response.read())
        print(f"Successfully downloaded font: {local_path}")
        return local_path
    except Exception as e:
        print(f"Failed to download font {font_key}: {e}. Fallback will be used.")
        return ""

_font_cache = {}

def get_font(font_family: str, size: int, is_bold: bool = False) -> ImageFont.ImageFont:
    """
    Returns a PIL ImageFont object for the requested family and size.
    Falls back gracefully if the font is not installed or cannot be downloaded.
    Uses an in-memory cache to prevent file system leaks and overhead.
    """
    key = (font_family, size, is_bold)
    if key in _font_cache:
        return _font_cache[key]
        
    font_obj = _get_font_uncached(font_family, size, is_bold)
    _font_cache[key] = font_obj
    return font_obj

def _get_font_uncached(font_family: str, size: int, is_bold: bool = False) -> ImageFont.ImageFont:
    suffix = "Bold" if is_bold else "Regular"
    
    # 1. Try to find the local path in the assets/fonts/ directory or its subfolders
    local_path = get_local_font_path(font_family, suffix)
    if local_path:
        try:
            return ImageFont.truetype(local_path, size)
        except Exception as e:
            print(f"Failed to load local font {font_family}-{suffix} from {local_path}: {e}")
            
    # 2. Try online downloading as fallback if it is a known family
    if font_family in ["Mulish", "Nunito"]:
        font_key = f"{font_family}-{suffix}"
        download_path = ensure_font_downloaded(font_key)
        if download_path and os.path.exists(download_path):
            try:
                return ImageFont.truetype(download_path, size)
            except Exception:
                pass
                
    # 3. System fallbacks based on requested styling
    fallbacks = []
    if font_family == "Nunito":
        fallbacks = ["segoeuib.ttf" if is_bold else "segoeui.ttf", "arialbd.ttf" if is_bold else "arial.ttf"]
    elif font_family == "Mulish":
        fallbacks = ["segoeuib.ttf" if is_bold else "segoeui.ttf", "arialbd.ttf" if is_bold else "arial.ttf"]
    else:
        fallbacks = ["arialbd.ttf" if is_bold else "arial.ttf"]
        
    for f in fallbacks:
        try:
            return ImageFont.truetype(f, size)
        except IOError:
            continue
            
    # Final default fallback
    return ImageFont.load_default()


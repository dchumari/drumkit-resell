import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

import shutil
from PIL import Image
from cover_generator import get_background_image

def test_downloader():
    cache_dir = "assets/cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    # Test valid download
    url = "https://picsum.photos/100/100"
    img = get_background_image(url, cache_dir)
    assert img is not None
    assert isinstance(img, Image.Image)
    assert img.size == (100, 100)
    
    # Test cache hit
    img2 = get_background_image(url, cache_dir)
    assert img2 is not None
    
    # Clean cache
    shutil.rmtree(cache_dir, ignore_errors=True)

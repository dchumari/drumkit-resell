import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from PIL import Image
import cover_generator
from config import ASSETS_DIR

def test_branding_overlays():
    # Verify the paths exist in the workspace assets folder
    pa_path = os.path.join(ASSETS_DIR, "parental_advisory.png")
    pi_path = os.path.join(ASSETS_DIR, "producer_icon_or_logo(1).png")
    ml_path = os.path.join(ASSETS_DIR, "producer_icon_or_logo.png")
    
    assert os.path.exists(pa_path), f"Missing {pa_path}"
    assert os.path.exists(pi_path), f"Missing {pi_path}"
    assert os.path.exists(ml_path), f"Missing {ml_path}"
    
    # Generate cover art and make sure it loads files without throwing exception
    out_cover = "test_output/test_branding_cover.png"
    os.makedirs("test_output", exist_ok=True)
    
    cover_generator.generate_cover_art("Branding Test Kit", "Trap", out_cover, pack_type="Drumkit")
    assert os.path.exists(out_cover)
    
    # Clean up test output file
    if os.path.exists(out_cover):
        os.remove(out_cover)

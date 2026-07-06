import os
import sys
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from cover_generator import generate_cover_art
from mockup_generator import generate_3d_mockup

def test_branding_overlays():
    # Make sure mock images exist in assets
    assert os.path.exists("assets/parental_advisory.png")
    assert os.path.exists("assets/producer_icon_or_logo.png")
    assert os.path.exists("assets/producer_icon_or_logo(1).png")
    
    # Run generative cover art to verify no overlay exceptions
    cover_path = "test_output/test_overlay_cover.png"
    generate_cover_art("Overlay Test Pack", "Trap", cover_path, pack_type="Drumkit")
    assert os.path.exists(cover_path)
    
    # Run 3D mockup to verify no exceptions
    mockup_path = "test_output/test_overlay_mockup.png"
    generate_3d_mockup(cover_path, mockup_path, "Overlay Test Pack", "Trap", pack_type="Drumkit")
    assert os.path.exists(mockup_path)
    
    # Clean up test output
    if os.path.exists(cover_path):
        os.remove(cover_path)
    if os.path.exists(mockup_path):
        os.remove(mockup_path)

import os
import sys
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from mockup_generator import generate_spine

def test_spine_art():
    os.makedirs("test_output", exist_ok=True)
    cover_path = "test_output/temp_cover.png"
    # Create fake cover
    cover = Image.new("RGB", (1200, 1200), (100, 50, 150))
    cover.save(cover_path)
    
    # Generate spine
    spine = generate_spine(
        cover_path, 
        height=1200, 
        width=120, 
        text="APEX DRUMKIT", 
        pack_type="Drumkit", 
        color_palette=((10, 10, 15), (25, 45, 30), (0, 240, 120))
    )
    assert spine is not None
    assert spine.size == (120, 1200)
    
    # Verify it is not a crop from the cover (color should be matte charcoal/black instead of cover's purple)
    pixel = spine.getpixel((10, 500))
    assert pixel == (18, 18, 20)
    
    os.remove(cover_path)

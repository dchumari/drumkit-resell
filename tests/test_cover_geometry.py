import os
import sys
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from cover_generator import draw_generative_elements

def test_draw_generative_elements():
    img = Image.new("RGB", (1200, 1200), (0, 0, 0))
    # Test different pack types to make sure they run without error
    draw_generative_elements(img, "Drumkit", (0, 255, 0))
    draw_generative_elements(img, "Loopkit", (255, 0, 255))
    draw_generative_elements(img, "One-shot", (0, 255, 255))
    assert True

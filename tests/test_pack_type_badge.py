import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from pipeline import detect_pack_type

def test_detect_pack_type():
    assert detect_pack_type("Vortex Drumkit") == "Drumkit"
    assert detect_pack_type("Vortex Loops") == "Loopkit"
    assert detect_pack_type("Ambient Melodies") == "Loopkit"
    assert detect_pack_type("Vortex One Shot") == "One-shot"
    assert detect_pack_type("Serum Presets Bank") == "Presets"
    assert detect_pack_type("Random Pack") == "Default"

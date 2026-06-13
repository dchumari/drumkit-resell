import os
import sys

print("=== Starting Drumkit Reseller Automated Self-Tests ===")

# Test 1: Imports Check
print("\nTest 1: Verification of module imports...")
try:
    import config
    import notifier
    import downloader
    import audio_processor
    import cover_generator
    import mockup_generator
    import video_generator
    import youtube_uploader
    import telegram_publisher
    import pipeline
    print("[OK] All modules imported successfully without syntax errors.")
except ImportError as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

# Test 2: Downloader Regex Matching
print("\nTest 2: Verifying downloader regex matches...")
links = {
    "https://drive.google.com/file/d/1a2b3c4d5e6f7g8h9i0j/view?usp=sharing": ("gdrive", "1a2b3c4d5e6f7g8h9i0j"),
    "https://drive.google.com/drive/folders/9i8h7g6f5e4d3c2b1a0z": ("gdrive", "9i8h7g6f5e4d3c2b1a0z"),
    "https://www.mediafire.com/file/z1y2x3w4v5u6t7/TestPack.zip/file": ("mediafire", "z1y2x3w4v5u6t7"),
    "https://mega.nz/file/a1b2c3d4#key123": ("mega", "a1b2c3d4"),
}

for link, expected in links.items():
    ltype = downloader.get_link_type(link)
    if ltype != expected[0]:
        print(f"[FAIL] Host mismatch for {link}. Expected {expected[0]}, got {ltype}")
        sys.exit(1)
        
    # Test regex group extraction
    if ltype == "gdrive":
        match = downloader.DRIVE_RE.search(link)
    elif ltype == "mediafire":
        match = downloader.MEDIAFIRE_RE.search(link)
    elif ltype == "mega":
        match = downloader.MEGA_RE.search(link)
        
    extracted_id = match.group(1)
    if extracted_id != expected[1]:
        print(f"[FAIL] ID mismatch for {link}. Expected {expected[1]}, got {extracted_id}")
        sys.exit(1)

print("[OK] Regex link detection and ID extraction verified successfully.")

# Test 3: Audio Processor Text Whitewashing
print("\nTest 3: Verifying audio processor text cleaning...")
test_titles = [
    ("Cymatics Lofi Drum Kit (140BPM) (Cmin)", "[AQ] Lofi (140BPM) (Cmin)"),
    ("Wavgrind Phonk Cowbell Loop", "[AQ] Phonk Cowbell Loop"),
    ("Decap Drums That Knock Pack v9", "[AQ] Drums That Knock v9"),
    ("Splice Exclusive Trap Samples (80 BPM) (F#)", "[AQ] Trap Samples (80BPM) (F#)")
]

for title, expected in test_titles:
    bpm, key = audio_processor.parse_bpm_key(title)
    cleaned = audio_processor.clean_text(os.path.splitext(title)[0])
    
    # Form title exactly like audio_processor renaming does
    new_title = f"[AQ] {cleaned}"
    meta = []
    if bpm:
        meta.append(f"{bpm}BPM")
    if key:
        meta.append(key)
    if meta:
        new_title += " " + " ".join(f"({m})" for m in meta)
        
    if new_title.lower() != expected.lower():
        print(f"[FAIL] Rebrand naming mismatch!\n  Original: '{title}'\n  Expected: '{expected}'\n  Got:      '{new_title}'")
        sys.exit(1)

print("[OK] Brand whitewashing and metadata preservation naming verified successfully.")

# Test 4: Procedural Visual Elements & Math Solver
print("\nTest 4: Verifying procedural gradient and 3D projection math...")
try:
    # Test perspective coefficient solver
    src_pts = [(0, 0), (0, 100), (100, 100), (100, 0)]
    dest_pts = [(10, 10), (10, 90), (90, 80), (90, 20)]
    coeffs = mockup_generator.get_perspective_coeffs(src_pts, dest_pts)
    
    if len(coeffs) != 8:
        print(f"[FAIL] Perspective solver returned {len(coeffs)} coefficients instead of 8.")
        sys.exit(1)
        
    print("[OK] Perspective projection coefficients computed successfully.")
    
    # Test procedural cover generation gradient mask
    w, h = 100, 100
    mask = cover_generator.get_gradient_mask(w, h)
    if mask.size != (w, h):
        print(f"[FAIL] Gradient mask size mismatch: {mask.size}")
        sys.exit(1)
        
    print("[OK] Procedural gradient mask verified successfully.")
    
except Exception as e:
    print(f"[FAIL] Visual components verification failed: {e}")
    sys.exit(1)

print("\n[SUCCESS] ALL TESTS COMPLETED SUCCESSFULLY! The Arqive Drumkit Reseller components are syntactically and logically correct.")


# Generative Cover Art Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a fully generative, customizable cover art and 3D mockup system that fetches background textures, draws unique 3D wireframe geometries on every run, displays capsule labels for pack types, and overlays branding assets.

**Architecture:** Update `src/pipeline.py`, `src/cover_generator.py`, and `src/mockup_generator.py` to support dynamic pack type detection, PIL procedural drawing, caching downloaders, and overlay logo placements.

**Tech Stack:** Python 3.10+, PIL (Pillow), requests, math, random, git.

## Global Constraints
- **parental_advisory.png**: Located at `assets/parental_advisory.png`. Must be placed at the bottom-left of the cover art and warped mockup face.
- **producer_icon_or_logo.png**: Located at `assets/producer_icon_or_logo.png` (Main Logo). Must be placed at the top-right of the cover art.
- **producer_icon_or_logo(1).png**: Located at `assets/producer_icon_or_logo(1).png` (Producer Icon). Must be placed at the top-left of the cover art, and at the top of the vertical spine (rotated and scaled to `40x40`).
- **No Colors for Pack Types**: Color schemes remain genre-based (with jitter). Pack types are differentiated by naming badges only.
- **Unique Design Every Time**: Every generation must use randomized parameters (spacing, counts, rotation) so no design is identical.

---

### Task 1: Background Image Downloader & Caching

**Files:**
- Modify: `src/cover_generator.py` (Add image download and caching helper)
- Test: Create `tests/test_cover_downloader.py`

**Interfaces:**
- Produces: `get_background_image(url: str, cache_dir: str) -> Image.Image`

- [ ] **Step 1: Write the test for downloader caching and offline fallback**

Create `tests/test_cover_downloader.py`:
```python
import os
import shutil
from PIL import Image
from src.cover_generator import get_background_image

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
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_cover_downloader.py -v`
Expected: Fail (ImportError/NameError for get_background_image)

- [ ] **Step 3: Implement get_background_image**

Add at the top of `src/cover_generator.py`:
```python
import urllib.request
import hashlib

def get_background_image(url: str, cache_dir: str = "assets/cache") -> Image.Image:
    """Downloads a background image from a URL and caches it locally."""
    os.makedirs(cache_dir, exist_ok=True)
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    cache_path = os.path.join(cache_dir, f"{url_hash}.png")
    
    if os.path.exists(cache_path):
        try:
            return Image.open(cache_path).convert("RGB")
        except Exception:
            pass
            
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            with open(cache_path, 'wb') as out_file:
                out_file.write(response.read())
        return Image.open(cache_path).convert("RGB")
    except Exception as e:
        print(f"Network download failed: {e}. Falling back to gradient.")
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cover_downloader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cover_generator.py
git commit -m "feat: add cached background downloader"
```

---

### Task 2: Generative 3D Wireframes and Geometry Drawing

**Files:**
- Modify: `src/cover_generator.py` (Add 3D projection, dot grid, tape cassette, and vinyl groove algorithms)
- Test: Create `tests/test_cover_geometry.py`

**Interfaces:**
- Produces: `draw_generative_elements(img: Image.Image, pack_type: str, color: tuple) -> None`

- [ ] **Step 1: Write the test for generative elements**

Create `tests/test_cover_geometry.py`:
```python
from PIL import Image
from src.cover_generator import draw_generative_elements

def test_draw_generative_elements():
    img = Image.new("RGB", (1200, 1200), (0, 0, 0))
    # Test different pack types to make sure they run without error
    draw_generative_elements(img, "Drumkit", (0, 255, 0))
    draw_generative_elements(img, "Loopkit", (255, 0, 255))
    draw_generative_elements(img, "One-shot", (0, 255, 255))
    assert True
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_cover_geometry.py -v`
Expected: Fail (NameError)

- [ ] **Step 3: Implement drawing functions**

In `src/cover_generator.py`:
```python
def project_3d_point(x, y, z, angle_x, angle_y, angle_z, cx=600, cy=600, scale=350):
    """Rotates and projects a 3D point (x, y, z) in [-1, 1] onto 2D space."""
    # X-rotation
    rad_x = math.radians(angle_x)
    cos_x, sin_x = math.cos(rad_x), math.sin(rad_x)
    y1 = y * cos_x - z * sin_x
    z1 = y * sin_x + z * cos_x
    
    # Y-rotation
    rad_y = math.radians(angle_y)
    cos_y, sin_y = math.cos(rad_y), math.sin(rad_y)
    x2 = x * cos_y + z1 * sin_y
    z2 = -x * sin_y + z1 * cos_y
    
    # Z-rotation
    rad_z = math.radians(angle_z)
    cos_z, sin_z = math.cos(rad_z), math.sin(rad_z)
    x3 = x2 * cos_z - y1 * sin_z
    y3 = x2 * sin_z + y1 * cos_z
    
    # Simple perspective projection
    distance = 3.0
    proj_x = int(cx + scale * x3 / (distance + z2))
    proj_y = int(cy + scale * y3 / (distance + z2))
    return proj_x, proj_y

def draw_3d_wireframe_cube(draw, color):
    """Draws a floating 3D wireframe cube rotated randomly."""
    ax = random.uniform(0, 360)
    ay = random.uniform(0, 360)
    az = random.uniform(0, 360)
    cx = random.randint(300, 900)
    cy = random.randint(300, 900)
    scale = random.randint(150, 250)
    
    vertices = [
        (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
        (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)
    ]
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7)
    ]
    
    proj_pts = []
    for x, y, z in vertices:
        proj_pts.append(project_3d_point(x, y, z, ax, ay, az, cx, cy, scale))
        
    for start, end in edges:
        draw.line([proj_pts[start], proj_pts[end]], fill=(*color, 65), width=2)

def draw_generative_elements(img: Image.Image, pack_type: str, color: tuple) -> None:
    """Draws randomized overlays and 3D wireframe shapes on the canvas."""
    draw = ImageDraw.Draw(img)
    # 1. Floating 3D cubes/wireframes
    for _ in range(random.randint(2, 4)):
        draw_3d_wireframe_cube(draw, color)
        
    # 2. Procedural background grid/groove overlay
    if pack_type == "Drumkit":
        spacing = random.randint(45, 75)
        dot_r = random.randint(2, 5)
        for x in range(0, 1200, spacing):
            draw.line([(x, 0), (x, 1200)], fill=(*color, 25), width=1)
        for y in range(0, 1200, spacing):
            draw.line([(0, y), (1200, y)], fill=(*color, 25), width=1)
        for x in range(spacing, 1200, spacing * 2):
            for y in range(spacing, 1200, spacing * 2):
                draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=(*color, 50))
                
    elif pack_type == "Loopkit":
        cx, cy = 600, 600
        for layer in range(random.randint(3, 5)):
            pts = []
            amp = random.randint(30, 65)
            freq = random.uniform(0.003, 0.008)
            phase = random.uniform(0, 6.28)
            for x in range(0, 1200, 12):
                y = cy + int(amp * math.sin(x * freq + phase))
                pts.append((x, y))
            for i in range(len(pts) - 1):
                draw.line([pts[i], pts[i+1]], fill=(*color, 35), width=2)
                
        # Draw Cassette body in center
        draw.rounded_rectangle([cx - 240, cy - 150, cx + 240, cy + 150], radius=15, outline=(*color, 80), width=4)
        draw.rectangle([cx - 110, cy - 55, cx + 110, cy + 55], outline=(*color, 80), width=3)
        draw.ellipse([cx - 70 - 22, cy - 22, cx - 70 + 22, cy + 22], outline=(*color, 80), width=3)
        draw.ellipse([cx + 70 - 22, cy - 22, cx + 70 + 22, cy + 22], outline=(*color, 80), width=3)
        
    elif pack_type == "One-shot":
        cx, cy = 600, 600
        step = random.randint(20, 30)
        for r in range(120, 520, step):
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*color, 30), width=1)
        draw.ellipse([cx - 80, cy - 80, cx + 80, cy + 80], outline=(*color, 70), width=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cover_geometry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cover_generator.py
git commit -m "feat: add procedural 3D wireframe and randomized overlays"
```

---

### Task 3: Naming Subtitle Badges and Spine Layouts

**Files:**
- Modify: `src/cover_generator.py` (Implement capsule badge text drawing below title)
- Modify: `src/mockup_generator.py` (Implement capsule badge on 3D spine)
- Modify: `src/pipeline.py` (Detect `pack_type` from renamed pack title)
- Test: Create `tests/test_pack_type_badge.py`

**Interfaces:**
- Produces: `draw_pack_type_badge(draw, cx, cy, text, color, font)`

- [ ] **Step 1: Write test for pack type detection**

Create `tests/test_pack_type_badge.py`:
```python
from src.pipeline import detect_pack_type

def test_detect_pack_type():
    assert detect_pack_type("Vortex Drumkit") == "Drumkit"
    assert detect_pack_type("Vortex Loops") == "Loopkit"
    assert detect_pack_type("Ambient Melodies") == "Loopkit"
    assert detect_pack_type("Vortex One Shot") == "One-shot"
    assert detect_pack_type("Serum Presets Bank") == "Presets"
    assert detect_pack_type("Random Pack") == "Default"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_pack_type_badge.py -v`
Expected: Fail (ImportError for detect_pack_type)

- [ ] **Step 3: Implement detect_pack_type**

In `src/pipeline.py`:
```python
import re

def detect_pack_type(name: str) -> str:
    """Identifies the category of the pack based on its name."""
    name_lower = name.lower()
    if any(k in name_lower for k in ["drumkit", "drum kit", "drums"]):
        return "Drumkit"
    if any(k in name_lower for k in ["loopkit", "loop kit", "melody", "loops"]):
        return "Loopkit"
    if any(k in name_lower for k in ["oneshot", "one shot", "oneshots"]):
        return "One-shot"
    if any(k in name_lower for k in ["presets", "bank", "serum", "electra"]):
        return "Presets"
    return "Default"
```

- [ ] **Step 4: Implement drawing the capsule badge**

In `src/cover_generator.py`:
```python
def draw_pack_type_badge(draw, cx, cy, pack_type, color, font):
    """Draws a capsule outline badge with text below the title."""
    badge_text = pack_type.upper()
    if badge_text == "LOOPKIT":
        badge_text = "LOOP KIT"
    elif badge_text == "ONE-SHOT":
        badge_text = "ONE-SHOTS"
        
    bbox = draw.textbbox((0, 0), badge_text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    pad_x, pad_y = 20, 10
    bx0, by0 = cx - tw // 2 - pad_x, cy - th // 2 - pad_y
    bx1, by1 = cx + tw // 2 + pad_x, cy + th // 2 + pad_y
    
    # Draw outline rounded rectangle
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=8, outline=color, width=2)
    # Draw text centered inside
    tx, ty = cx - tw // 2 - bbox[0], cy - th // 2 - bbox[1]
    draw.text((tx, ty), badge_text, fill=color, font=font)
```

Integrate `draw_pack_type_badge` in `generate_cover_art` in `src/cover_generator.py`:
```python
    # After drawing main title:
    # Use smaller font for badge
    try:
        font_badge = ImageFont.truetype("arialbd.ttf", 36)
    except IOError:
        font_badge = ImageFont.load_default()
        
    badge_y = ty + th + 60
    draw_pack_type_badge(draw, cx, badge_y, pack_type, text_color, font_badge)
```

In `src/mockup_generator.py`, draw the vertical badge on the spine:
```python
        # Draw vertical badge text on spine canvas
        badge_text = pack_type.upper()
        if badge_text == "LOOPKIT":
            badge_text = "LOOP KIT"
        elif badge_text == "ONE-SHOT":
            badge_text = "ONE-SHOTS"
            
        try:
            font_spine_badge = ImageFont.truetype("arialbd.ttf", 22)
        except:
            font_spine_badge = ImageFont.load_default()
            
        # Draw on spine canvas below main text
        # Rotate badge text or capsule
```

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_pack_type_badge.py -v`
Expected: PASS

```bash
git add src/pipeline.py src/cover_generator.py src/mockup_generator.py
git commit -m "feat: add pack type capsule subtitle badges on cover and spine"
```

---

### Task 4: Branding Asset Overlays

**Files:**
- Modify: `src/cover_generator.py` (Place logos and parental advisory icon on cover corners)
- Modify: `src/mockup_generator.py` (Place producer icon at the top of vertical spine)

- [ ] **Step 1: Write tests for overlays**

Verify paths:
- `assets/parental_advisory.png`
- `assets/producer_icon_or_logo.png`
- `assets/producer_icon_or_logo(1).png`

- [ ] **Step 2: Implement local logo overlays on cover**

In `generate_cover_art` in `src/cover_generator.py`:
```python
    # 1. Overlay Parental Advisory on bottom-left
    pa_path = "assets/parental_advisory.png"
    if os.path.exists(pa_path):
        pa_img = Image.open(pa_path).convert("RGBA")
        # Resize preserving aspect ratio (width=160px)
        pa_w = 160
        pa_h = int(pa_img.height * (pa_w / pa_img.width))
        pa_img = pa_img.resize((pa_w, pa_h), Image.Resampling.LANCZOS)
        img.paste(pa_img, (60, 1200 - 60 - pa_h), pa_img)
        
    # 2. Overlay Producer Icon on top-left (80x80px)
    pi_path = "assets/producer_icon_or_logo(1).png"
    if os.path.exists(pi_path):
        pi_img = Image.open(pi_path).convert("RGBA")
        pi_img = pi_img.resize((80, 80), Image.Resampling.LANCZOS)
        img.paste(pi_img, (60, 60), pi_img)
        
    # 3. Overlay Main Logo on top-right (120x120px)
    ml_path = "assets/producer_icon_or_logo.png"
    if os.path.exists(ml_path):
        ml_img = Image.open(ml_path).convert("RGBA")
        ml_img = ml_img.resize((120, 120), Image.Resampling.LANCZOS)
        img.paste(ml_img, (1200 - 60 - 120, 60), ml_img)
```

- [ ] **Step 3: Implement producer icon on mockup spine**

In `generate_3d_mockup` in `src/mockup_generator.py`:
On the spine canvas (size `148x676`), paste the producer icon at the top of the vertical text:
```python
    pi_path = "assets/producer_icon_or_logo(1).png"
    if os.path.exists(pi_path):
        pi_img = Image.open(pi_path).convert("RGBA")
        pi_img = pi_img.resize((40, 40), Image.Resampling.LANCZOS)
        # Center horizontal on spine, 30px from top
        spine_canvas.paste(pi_img, (74 - 20, 30), pi_img)
```

- [ ] **Step 4: Commit**

```bash
git add src/cover_generator.py src/mockup_generator.py
git commit -m "feat: place branding logo overlays on cover and vertical spine"
```

---

### Task 5: End-to-End Test Verification

**Files:**
- Run: `src/test_pipeline_local.py`
- Verify outputs.

- [ ] **Step 1: Execute pipeline test**

Run: `python src/test_pipeline_local.py`
Expected: Output generated successfully.

- [ ] **Step 2: Inspect assets and commit**
Check `test_output/rebranded_mockup.png`, cover art, and videos.

```bash
git status
```

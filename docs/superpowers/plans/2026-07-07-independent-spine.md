# Independent Spine Mockup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the 3D mockup box spine (left side) to have its own solid dark styling, independent of the front cover art, with white vertical text and accent-colored capsule badge.

**Architecture:** Modify `src/mockup_generator.py` to draw the spine canvas independently from scratch.

**Tech Stack:** Python 3.10+, PIL (Pillow), git.

## Global Constraints
- **Spine Background**: Solid charcoal color `(18, 18, 20)`.
- **Spine Badge Color**: Drawn in the genre's accent color (passed via `color_palette` or resolved from `config.py`).
- **Main Text**: Solid white.
- **Producer Icon**: Paste at the top of the spine (`60x60px`).

---

### Task 1: Refactor Spine Generation in mockup_generator.py

**Files:**
- Modify: `src/mockup_generator.py` (Implement independent spine canvas drawing)
- Test: Create `tests/test_spine_art.py`

- [ ] **Step 1: Write test for independent spine generation**

Create `tests/test_spine_art.py`:
```python
import os
from PIL import Image
from src.mockup_generator import generate_spine

def test_spine_art():
    os.makedirs("test_output", exist_ok=True)
    cover_path = "test_output/temp_cover.png"
    # Create fake cover
    cover = Image.new("RGB", (1200, 1200), (100, 50, 150))
    cover.save(cover_path)
    
    # Generate spine
    spine = generate_spine(cover_path, height=1200, width=120, text="APEX DRUMKIT", pack_type="Drumkit", color_palette=((10, 10, 15), (25, 45, 30), (0, 240, 120)))
    assert spine is not None
    assert spine.size == (120, 1200)
    
    # Verify it is not a crop from the cover (color should be matte charcoal/black instead of purple)
    pixel = spine.getpixel((10, 500))
    assert pixel == (18, 18, 20)
    
    os.remove(cover_path)
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_spine_art.py -v`
Expected: Fail (getpixel returns cropped cover color instead of matte charcoal, or color_palette argument not accepted)

- [ ] **Step 3: Implement generate_spine**

Update `generate_spine` in `src/mockup_generator.py` to:
- Accept `color_palette = None`.
- Initialize `spine = Image.new("RGB", (width, height), (18, 18, 20))`.
- Draw a vertical right-edge border: `draw.line([(width - 1, 0), (width - 1, height)], fill=(35, 35, 40), width=1)`.
- Use the accent color from `color_palette[2]` or `GENRE_COLORS[genre]["text_color"]` for the capsule badge.

```python
def generate_spine(cover_path: str, height: int = 1200, width: int = 120, text: str = "ARQIVE COLLECTION", pack_type: str = "Default", color_palette=None, genre: str = "Default") -> Image.Image:
    """Generates an independent 2D spine strip with a solid matte charcoal background."""
    # 1. Base spine texture: Solid charcoal/black background
    spine = Image.new("RGB", (width, height), (18, 18, 20))
    draw = ImageDraw.Draw(spine)
    
    # Subtle right border edge divider
    draw.line([(width - 1, 0), (width - 1, height)], fill=(35, 35, 40), width=1)
    
    # Resolve accent color for the capsule badge
    accent_color = (255, 160, 30) # Default orange
    if color_palette:
        accent_color = color_palette[2]
    else:
        gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
        accent_color = gconfig["text_color"]
        
    # 2. Draw vertical rotated main text
    try:
        font_spine = ImageFont.truetype("arialbd.ttf", 26)
        font_spine_badge = ImageFont.truetype("arialbd.ttf", 16)
    except IOError:
        font_spine = ImageFont.load_default()
        font_spine_badge = ImageFont.load_default()
        
    bbox = draw.textbbox((0, 0), text, font=font_spine)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    txt_img = Image.new("RGBA", (tw + 40, th + 20), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt_img)
    td.text((20, 10), text, fill=(245, 245, 250, 220), font=font_spine)
    
    rotated_txt = txt_img.rotate(270, expand=True)
    rw, rh = rotated_txt.size
    sx = (width - rw) // 2
    sy = (height - rh) // 2
    spine.paste(rotated_txt, (sx, sy), rotated_txt)
    
    # 3. Draw vertical rotated pack-type capsule badge below main text
    badge_text = pack_type.upper()
    if badge_text == "LOOPKIT":
        badge_text = "LOOP KIT"
    elif badge_text == "ONE-SHOT":
        badge_text = "ONE-SHOTS"
        
    if badge_text != "DEFAULT":
        badge_bbox = draw.textbbox((0, 0), badge_text, font=font_spine_badge)
        btw, bth = badge_bbox[2] - badge_bbox[0], badge_bbox[3] - badge_bbox[1]
        
        pad_x, pad_y = 12, 6
        badge_canvas_w = btw + pad_x * 2 + 10
        badge_canvas_h = bth + pad_y * 2 + 10
        
        badge_img = Image.new("RGBA", (badge_canvas_w, badge_canvas_h), (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge_img)
        
        # Draw capsule outline using accent color
        bd.rounded_rectangle([5, 5, badge_canvas_w - 5, badge_canvas_h - 5], radius=6, outline=(*accent_color, 180), width=2)
        bd.text((5 + pad_x, 5 + pad_y), badge_text, fill=(*accent_color, 200), font=font_spine_badge)
        
        rotated_badge = badge_img.rotate(270, expand=True)
        rbw, rbh = rotated_badge.size
        
        bsx = (width - rbw) // 2
        bsy = sy + rh + 40
        if bsy + rbh < height - 60:
            spine.paste(rotated_badge, (bsx, bsy), rotated_badge)
            
    # 4. Paste Producer Icon at top of spine (60x60px)
    pi_path = os.path.join(ASSETS_DIR, "producer_icon_or_logo(1).png")
    if os.path.exists(pi_path):
        try:
            pi_img = Image.open(pi_path).convert("RGBA")
            pi_img = pi_img.resize((60, 60), Image.Resampling.LANCZOS)
            spine.paste(pi_img, ((width - 60) // 2, 60), pi_img)
        except Exception as e:
            print(f"Error pasting producer icon: {e}")
            
    return spine
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_spine_art.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mockup_generator.py
git commit -m "feat: refactor generate_spine to draw solid matte charcoal background"
```

---

### Task 2: Pass Genre and Color Palette to generate_spine

**Files:**
- Modify: `src/mockup_generator.py:165-175` (Inside `generate_3d_mockup`)

- [ ] **Step 1: Update generate_3d_mockup call site**

Modify `spine_img` generation inside `generate_3d_mockup`:
```python
    spine_img = generate_spine(
        cover_path, 
        height=1200, 
        width=120, 
        text=pack_name.upper(), 
        pack_type=pack_type, 
        color_palette=color_palette, 
        genre=genre
    ).convert("RGBA")
```

- [ ] **Step 2: Commit**

```bash
git add src/mockup_generator.py
git commit -m "feat: pass color_palette and genre to generate_spine inside generate_3d_mockup"
```

---

### Task 3: Verify E2E Outputs

- [ ] **Step 1: Execute local pipeline test**

Run: `python src/test_pipeline_local.py --name "Apex Drumkit" --genre "Trap"`
Expected: Output generated successfully.

- [ ] **Step 2: Visually verify the rebranded mockup**

Check `test_output/rebranded_mockup.png` to confirm the left spine shows the solid matte charcoal background, while the front face shows the photographic Picsum cover background!

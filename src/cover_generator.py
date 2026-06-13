import os
import re
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import GENRE_COLORS, ASSETS_DIR

SIZE = 1200

def get_gradient_mask(w: int, h: int) -> Image.Image:
    """Generates a vertical gradient mask."""
    mask = Image.new("L", (1, h))
    for y in range(h):
        mask.putpixel((0, y), int(255 * (y / h)))
    return mask.resize((w, h))

def generate_gradient(w: int, h: int, color1: tuple, color2: tuple) -> Image.Image:
    """Creates a smooth vertical gradient image."""
    base = Image.new("RGB", (w, h), color1)
    top = Image.new("RGB", (w, h), color2)
    mask = get_gradient_mask(w, h)
    base.paste(top, (0, 0), mask)
    return base

def draw_topographic_lines(img: Image.Image, color: tuple, count: int = 10):
    """Draws topographical curved lines on the background."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    random.seed(42)  # Keep designs reproducible
    for layer in range(count):
        topo_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        td = ImageDraw.Draw(topo_img)
        yb = h * 0.4 + layer * 25
        amp = 20 + layer * 6
        pts = []
        for i in range(80):
            x = int(i * w / 79)
            y = int(yb + amp * math.sin(i * 0.2 + layer * 0.5) +
                    amp * 0.5 * math.sin(i * 0.55 + 2.0))
            pts.append((x, y))
        for i in range(len(pts) - 1):
            td.line([pts[i], pts[i + 1]], fill=(*color, 40), width=1)
        img.paste(Image.alpha_composite(img.convert("RGBA"), topo_img).convert("RGB"))

def draw_stardust(img: Image.Image, color: tuple, count: int = 400):
    """Adds faint glowing dust particles to the background."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = random.randint(0, w - 1), random.randint(0, h - 1)
        r = random.randint(1, 3)
        a = random.randint(30, 150)
        # Create small glowing circles
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    px, py = x + dx, y + dy
                    if 0 <= px < w and 0 <= py < h:
                        o = img.getpixel((px, py))
                        blend = tuple(int(o[i] + (color[i] - o[i]) * a / 255) for i in range(3))
                        img.putpixel((px, py), blend)

def generate_cover_art(pack_name: str, genre: str, output_path: str) -> str:
    """
    Generates a full 1200x1200px rebranded cover art image 
    customized by genre and saves it to output_path.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Resolve genre config
    gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
    color1, color2 = gconfig["bg_gradient"]
    text_color = gconfig["text_color"]
    border_color = gconfig["border_color"]
    overlay_filename = gconfig["overlay"]
    
    # 1. Base gradient
    img = generate_gradient(SIZE, SIZE, color1, color2)
    
    # 2. Topo lines & stardust
    draw_topographic_lines(img, text_color, count=8)
    draw_stardust(img, text_color, count=500)
    
    # 3. Apply PNG geometric overlay if specified
    if overlay_filename:
        overlay_path = os.path.join(ASSETS_DIR, overlay_filename)
        if os.path.exists(overlay_path):
            try:
                overlay_img = Image.open(overlay_path).convert("RGBA")
                # Resize overlay to fit cover
                overlay_img = overlay_img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
                # Blend using alpha channel
                base_rgba = img.convert("RGBA")
                blended = Image.alpha_composite(base_rgba, overlay_img)
                img = blended.convert("RGB")
            except Exception as e:
                print(f"Error loading cover art overlay {overlay_filename}: {e}")
    
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    try:
        font_brand = ImageFont.truetype("arial.ttf", 18)
        font_title = ImageFont.truetype("arialbd.ttf", 140)
    except IOError:
        font_brand = ImageFont.load_default()
        font_title = ImageFont.load_default()
        
    cx, cy = SIZE // 2, SIZE // 2
    
    # Format pack name: e.g. uppercase
    display_title = clean_title_for_cover(pack_name)
    
    # Draw 3D typography shadow layers (dark purple/grey shadows)
    for depth in range(12, 0, -1):
        ox, oy = depth * 2, depth * 2
        shade = int(15 + depth * 3)
        bbox = draw.textbbox((0, 0), display_title, font=font_title)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx, ty = cx - tw // 2 + ox, cy - th // 2 + oy
        draw.text((tx, ty), display_title, fill=(shade, shade - 5, shade + 8), font=font_title)
        
    # Draw primary text
    bbox = draw.textbbox((0, 0), display_title, font=font_title)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx, ty = cx - tw // 2, cy - th // 2
    draw.text((tx, ty), display_title, fill=(245, 245, 250), font=font_title)
    
    # Draw inner neon glow
    glow_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_img)
    gd.text((tx, ty), display_title, fill=(*text_color, 180), font=font_title)
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=8))
    img = Image.alpha_composite(img.convert("RGBA"), glow_img).convert("RGB")
    
    # Draw crisp front white text again
    draw = ImageDraw.Draw(img)
    draw.text((tx, ty), display_title, fill=(255, 255, 255), font=font_title)
    
    # 4. Headers and footers
    header_text = "ARQIVE SAMPLE COLLECTION"
    bbox_h = draw.textbbox((0, 0), header_text, font=font_brand)
    hw = bbox_h[2] - bbox_h[0]
    draw.text((cx - hw // 2, 28), header_text, fill=border_color, font=font_brand)
    
    footer_text = f"{genre.upper()} PREMIUM SAMPLE PACK"
    bbox_f = draw.textbbox((0, 0), footer_text, font=font_brand)
    fw = bbox_f[2] - bbox_f[0]
    draw.text((cx - fw // 2, SIZE - 46), footer_text, fill=border_color, font=font_brand)
    
    # 5. Outlined border
    draw.rectangle([8, 8, SIZE - 9, SIZE - 9], outline=border_color, width=3)
    
    img.save(output_path)
    print(f"Cover art generated: {output_path}")
    return output_path

def clean_title_for_cover(name: str) -> str:
    """Simplifies the pack name for big 3D printing on the cover."""
    # Strip Arqive prefixes
    title = name.replace("Arqive", "").replace("[AQ]", "").replace("Pack", "").strip()
    # Remove numbers and brackets
    title = re.sub(r"#\d+", "", title)
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"\[.*?\]", "", title)
    title = title.strip().upper()
    return title if title else "PACK"

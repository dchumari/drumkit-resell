import os
import re
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import GENRE_COLORS, ASSETS_DIR
import urllib.request
import hashlib

SIZE = 1200

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
    # Use random state that is not seeded by time to make each run truly unique
    for _ in range(random.randint(2, 4)):
        draw_3d_wireframe_cube(draw, color)
        
    # 2. Procedural background grid/groove overlay
    if pack_type == "Drumkit":
        spacing = random.randint(45, 75)
        dot_r = random.randint(2, 5)
        for x in range(0, SIZE, spacing):
            draw.line([(x, 0), (x, SIZE)], fill=(*color, 25), width=1)
        for y in range(0, SIZE, spacing):
            draw.line([(0, y), (SIZE, y)], fill=(*color, 25), width=1)
        for x in range(spacing, SIZE, spacing * 2):
            for y in range(spacing, SIZE, spacing * 2):
                draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=(*color, 50))
                
    elif pack_type == "Loopkit":
        cx, cy = SIZE // 2, SIZE // 2
        for layer in range(random.randint(3, 5)):
            pts = []
            amp = random.randint(30, 65)
            freq = random.uniform(0.003, 0.008)
            phase = random.uniform(0, 6.28)
            for x in range(0, SIZE, 12):
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
        cx, cy = SIZE // 2, SIZE // 2
        step = random.randint(20, 30)
        for r in range(120, 520, step):
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*color, 30), width=1)
        draw.ellipse([cx - 80, cy - 80, cx + 80, cy + 80], outline=(*color, 70), width=2)


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

def generate_cover_art(pack_name: str, genre: str, output_path: str, color_palette=None) -> str:
    """
    Generates a full 1200x1200px rebranded cover art image 
    customized by genre and saves it to output_path.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Resolve genre config
    gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
    if color_palette:
        color1, color2 = color_palette[0], color_palette[1]
    else:
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

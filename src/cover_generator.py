import os
import re
import math
import random
import urllib.request
import hashlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import GENRE_COLORS, ASSETS_DIR, MULTIPLE_STYLES
from font_manager import get_font

SIZE = 1200


def get_background_image(url: str, cache_dir: str = "assets/cache", cache_key: str = None) -> Image.Image:
    """Downloads a background image from a URL and caches it locally under a cache key."""
    os.makedirs(cache_dir, exist_ok=True)
    key_source = cache_key if cache_key else url
    url_hash = hashlib.md5(key_source.encode('utf-8')).hexdigest()
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
        print(f"Downloading background from {url}...")
        with urllib.request.urlopen(req, timeout=10) as response:
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

def generate_cover_art(pack_name: str, genre: str, output_path: str, color_palette=None, pack_type: str = "Default", style: str = None) -> str:
    """
    Generates a full 1200x1200px rebranded cover art image 
    customized by genre and saves it to output_path.
    Each visual style has a structurally unique cover layout.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    style_key = style if (style and style in MULTIPLE_STYLES) else "Default"
    
    # 1. Resolve typography font family
    if style and style in MULTIPLE_STYLES:
        font_family = MULTIPLE_STYLES[style]["font_family"]
        overlay_filename = None
    else:
        font_family = "Nunito"
        gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
        overlay_filename = gconfig["overlay"]
        
    # 2. Resolve colors (prioritize passed color_palette override)
    if color_palette:
        color1, color2, text_color = color_palette
        border_color = text_color
    elif style and style in MULTIPLE_STYLES:
        sconfig = MULTIPLE_STYLES[style]
        color1, color2 = sconfig["bg_gradient"]
        text_color = sconfig["text_color"]
        border_color = sconfig["border_color"]
    else:
        gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
        color1, color2 = gconfig["bg_gradient"]
        text_color = gconfig["text_color"]
        border_color = gconfig["border_color"]

    
    # 1. Base gradient
    img = generate_gradient(SIZE, SIZE, color1, color2)
    
    # Load background texture if available
    bg_img = None
    local_bg_dir = os.path.join(ASSETS_DIR, "backgrounds")
    if os.path.exists(local_bg_dir):
        local_bgs = [f for f in os.listdir(local_bg_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if local_bgs:
            try:
                bg_img = Image.open(os.path.join(local_bg_dir, random.choice(local_bgs))).convert("RGB")
                print("Loaded background from local assets.")
            except Exception:
                pass
                
    if bg_img is None:
        # Download from picsum
        picsum_url = "https://picsum.photos/1200/1200"
        bg_img = get_background_image(picsum_url, cache_key=f"{picsum_url}_{pack_name}")
        
    if bg_img is not None:
        bg_img = bg_img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        bg_gray = bg_img.convert("L")
        # Blend the grayscale texture onto the base gradient
        img = Image.blend(img, Image.merge("RGB", (bg_gray, bg_gray, bg_gray)), 0.3)
    
    draw = ImageDraw.Draw(img)
    
    # 2. Draw styled graphics
    if style_key == "neon_sunset":
        # Draw background cyberpunk grids
        for grid_y in range(100, SIZE, 100):
            draw.line([(0, grid_y), (SIZE, grid_y)], fill=(*border_color, 40), width=1)
        for grid_x in range(100, SIZE, 100):
            draw.line([(grid_x, 0), (grid_x, SIZE)], fill=(*border_color, 40), width=1)
        # Glowing double neon frame
        draw.rectangle([30, 30, SIZE - 31, SIZE - 31], outline=border_color, width=3)
        draw.rectangle([40, 40, SIZE - 41, SIZE - 41], outline=border_color, width=1)
        draw_topographic_lines(img, text_color, count=6)
        
    elif style_key == "pastel_minimalist":
        # Pastel Minimalist has clean Swiss layout: no topo lines, no stardust
        draw.rectangle([40, 40, SIZE - 40, SIZE - 40], outline=border_color, width=2)
        
    elif style_key == "rounded_sidebar":
        # Left sidebar rectangle block
        draw.rectangle([0, 0, 320, SIZE], fill=(*color1, 255))
        draw.line([(319, 0), (319, SIZE)], fill=border_color, width=2)
        draw_topographic_lines(img, text_color, count=8)
        draw_stardust(img, text_color, count=300)
        
    elif style_key == "floating_badge":
        # Floating badge (no background card)
        draw_topographic_lines(img, text_color, count=8)
        draw_stardust(img, text_color, count=500)
        
    elif style_key in ("asymmetric_float", "asymmetric_flow"):
        # Asymmetric float (no background card)
        draw_topographic_lines(img, text_color, count=10)
        draw_stardust(img, text_color, count=400)
        
    else:
        # Standard Arqive design
        draw_topographic_lines(img, text_color, count=8)
        draw_stardust(img, text_color, count=500)
        if overlay_filename:
            overlay_path = os.path.join(ASSETS_DIR, overlay_filename)
            if os.path.exists(overlay_path):
                try:
                    overlay_img = Image.open(overlay_path).convert("RGBA")
                    overlay_img = overlay_img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
                    base_rgba = img.convert("RGBA")
                    blended = Image.alpha_composite(base_rgba, overlay_img)
                    img = blended.convert("RGB")
                    draw = ImageDraw.Draw(img)
                except Exception as e:
                    print(f"Error loading cover art overlay {overlay_filename}: {e}")
                    
    # Load style-specific fonts
    font_brand = get_font(font_family, 18)
    font_title = get_font(font_family, 140, is_bold=True)
    
    # Calculate title center depending on sidebar presence
    cx, cy = SIZE // 2, SIZE // 2
    if style_key == "rounded_sidebar":
        cx = (SIZE + 320) // 2  # Offset to the right
        
    # Format pack name: e.g. uppercase
    display_title = clean_title_for_cover(pack_name)
    
    # Title Shadow Layers (Skip for pastel_minimalist)
    if style_key != "pastel_minimalist":
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
    
    # Draw Genre Badge above the title
    font_genre_badge = get_font(font_family, 32, is_bold=True)
    genre_text = f"  {genre.upper()}  "
    bbox_g = draw.textbbox((0, 0), genre_text, font=font_genre_badge)
    gw, gh = bbox_g[2] - bbox_g[0], bbox_g[3] - bbox_g[1]
    
    gbx0, gby0 = cx - gw // 2 - 12, ty - 75
    gbx1, gby1 = cx + gw // 2 + 12, ty - 75 + gh + 14
    draw.rounded_rectangle([gbx0, gby0, gbx1, gby1], radius=6, outline=text_color, width=2)
    draw.text((cx - gw // 2 - bbox_g[0], gby0 + 7 - bbox_g[1]), genre_text, fill=text_color, font=font_genre_badge)

    font_badge = get_font(font_family, 36, is_bold=True)
        
    badge_y = ty + th + 60
    draw_pack_type_badge(draw, cx, badge_y, pack_type, text_color, font_badge)
    
    # 4. Headers and footers
    header_text = "ARQIVE SAMPLE COLLECTION"
    bbox_h = draw.textbbox((0, 0), header_text, font=font_brand)
    hw = bbox_h[2] - bbox_h[0]
    draw.text((cx - hw // 2, 28), header_text, fill=border_color, font=font_brand)
    
    footer_text = f"{genre.upper()} PREMIUM SAMPLE PACK"
    bbox_f = draw.textbbox((0, 0), footer_text, font=font_brand)
    fw = bbox_f[2] - bbox_f[0]
    draw.text((cx - fw // 2, SIZE - 46), footer_text, fill=border_color, font=font_brand)
    
    # 5. Outlined border (removed to clean up mockup front face edges)
    # draw.rectangle([8, 8, SIZE - 9, SIZE - 9], outline=border_color, width=3)
    
    # 6. Apply Branding Overlays
    rgba_img = img.convert("RGBA")
    
    # Bottom-left: Parental Advisory
    pa_path = os.path.join(ASSETS_DIR, "parental_advisory.png")
    if os.path.exists(pa_path):
        try:
            pa_img = Image.open(pa_path).convert("RGBA")
            pa_w = 160
            pa_h = int(pa_img.height * (pa_w / pa_img.width))
            pa_img = pa_img.resize((pa_w, pa_h), Image.Resampling.LANCZOS)
            rgba_img.paste(pa_img, (60, SIZE - 60 - pa_h), pa_img)
            print("Pasted Parental Advisory logo at bottom-left.")
        except Exception as e:
            print(f"Error loading parental advisory logo: {e}")
            
    # Top-left: Producer Icon (80x80px)
    pi_path = os.path.join(ASSETS_DIR, "producer_icon_or_logo(1).png")
    if os.path.exists(pi_path):
        try:
            pi_img = Image.open(pi_path).convert("RGBA")
            pi_img = pi_img.resize((80, 80), Image.Resampling.LANCZOS)
            rgba_img.paste(pi_img, (60, 60), pi_img)
            print("Pasted Producer Icon at top-left.")
        except Exception as e:
            print(f"Error loading producer icon: {e}")
            
    # Top-right: Main Logo (120x120px)
    ml_path = os.path.join(ASSETS_DIR, "producer_icon_or_logo.png")
    if os.path.exists(ml_path):
        try:
            ml_img = Image.open(ml_path).convert("RGBA")
            ml_img = ml_img.resize((120, 120), Image.Resampling.LANCZOS)
            rgba_img.paste(ml_img, (SIZE - 60 - 120, 60), ml_img)
            print("Pasted Main Logo at top-right.")
        except Exception as e:
            print(f"Error loading main logo: {e}")
            
    img = rgba_img.convert("RGB")
    
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

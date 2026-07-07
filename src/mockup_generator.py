import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import GENRE_COLORS, ASSETS_DIR

def solve_linear_system(matrix, vector):
    """Gaussian elimination solver for NxN matrix in pure Python."""
    n = len(vector)
    # Forward elimination
    for i in range(n):
        # Pivot search
        max_el = abs(matrix[i][i])
        max_row = i
        for k in range(i + 1, n):
            if abs(matrix[k][i]) > max_el:
                max_el = abs(matrix[k][i])
                max_row = k
        # Swap rows
        matrix[i], matrix[max_row] = matrix[max_row], matrix[i]
        vector[i], vector[max_row] = vector[max_row], vector[i]
        
        # Zero out below pivot
        for k in range(i + 1, n):
            if matrix[i][i] == 0:
                continue
            c = -matrix[k][i] / matrix[i][i]
            for j in range(i, n):
                if i == j:
                    matrix[k][j] = 0
                else:
                    matrix[k][j] += c * matrix[i][j]
            vector[k] += c * vector[i]
            
    # Backward substitution
    res = [0] * n
    for i in range(n - 1, -1, -1):
        if matrix[i][i] == 0:
            res[i] = 0
            continue
        res[i] = vector[i] / matrix[i][i]
        for k in range(i - 1, -1, -1):
            vector[k] -= matrix[k][i] * res[i]
    return res

def get_perspective_coeffs(src_pts, dest_pts):
    """Computes the 8 perspective coefficients to map src_pts to dest_pts."""
    matrix = []
    vector = []
    for (x, y), (u, v) in zip(src_pts, dest_pts):
        matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        vector.append(u)
        vector.append(v)
    return solve_linear_system(matrix, vector)

def generate_spine(cover_path: str, height: int = 1200, width: int = 120, text: str = "ARQIVE COLLECTION", pack_type: str = "Default", color_palette=None, genre: str = "Default") -> Image.Image:
    """Generates an independent 2D spine strip with a solid matte charcoal background."""
    # 1. Base spine texture: Solid charcoal/black background
    spine = Image.new("RGB", (width, height), (18, 18, 20))
    draw = ImageDraw.Draw(spine)
    
    # Subtle right border edge divider
    draw.line([(width - 1, 0), (width - 1, height)], fill=(35, 35, 40), width=1)
    
    # Resolve accent color for the capsule badge
    accent_color = (255, 160, 30) # Default orange fallback
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
            print("Pasted producer icon on spine.")
        except Exception as e:
            print(f"Error pasting producer icon on spine: {e}")
            
    return spine

def draw_neon_outline(canvas: Image.Image, polygon_pts: list, color: tuple):
    """Draws multiple blurred layers of a line outline to create a neon glow around the polygon points."""
    pts = polygon_pts + [polygon_pts[0]]
    
    # 1. Thick blurred background glow (width 24, alpha 45, Gaussian blur 10)
    glow1 = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd1 = ImageDraw.Draw(glow1)
    gd1.line(pts, fill=(*color, 45), width=24, joint="round")
    glow1 = glow1.filter(ImageFilter.GaussianBlur(10))
    canvas.alpha_composite(glow1)
    
    # 2. Medium blurred overlay glow (width 12, alpha 95, Gaussian blur 4)
    glow2 = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd2 = ImageDraw.Draw(glow2)
    gd2.line(pts, fill=(*color, 95), width=12, joint="round")
    glow2 = glow2.filter(ImageFilter.GaussianBlur(4))
    canvas.alpha_composite(glow2)
    
    # 3. Crisp white neon core (width 3, alpha 220)
    glow3 = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd3 = ImageDraw.Draw(glow3)
    gd3.line(pts, fill=(255, 255, 255, 220), width=3, joint="round")
    canvas.alpha_composite(glow3)

def generate_3d_mockup(cover_path: str, output_path: str, pack_name: str, genre: str, color_palette=None, pack_type: str = "Default"):
    """Warps cover and spine into a 3D box mockup and saves it."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    canvas_size = (736, 736)
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    
    # Coordinates matching 736x736 parallel vector template
    B = (148, 98)
    C = (230, 60)
    D = (588, 127)
    E = (148, 647)
    F = (230, 676)
    G = (588, 623)
    
    # Define 3D perspectives coordinates
    # Spine (Left Face)
    spine_src = [(0, 0), (0, 1200), (120, 1200), (120, 0)]
    spine_dest = [B, E, F, C]
    
    # Front Cover Face
    front_src = [(0, 0), (0, 1200), (1200, 1200), (1200, 0)]
    front_dest = [C, F, G, D]
    
    # 1. Draw soft drop shadow behind the box
    shadow_canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_canvas)
    # Draw soft polygon shadow base under the box
    sd.polygon([(140, 650), (230, 685), (600, 630), (600, 620), (140, 635)], fill=(0, 0, 0, 120))
    shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=15))
    canvas.paste(shadow_canvas, (0, 0), shadow_canvas)
    
    # 2. Warp Spine Left Face
    spine_img = generate_spine(cover_path, height=1200, width=120, text=pack_name.upper(), pack_type=pack_type, color_palette=color_palette, genre=genre).convert("RGBA")
    spine_coeffs = get_perspective_coeffs(spine_dest, spine_src)
    warped_spine = spine_img.transform(canvas_size, Image.Transform.PERSPECTIVE, spine_coeffs, Image.Resampling.BILINEAR)
    canvas.paste(warped_spine, (0, 0), warped_spine)
    
    # 3. Warp Front Cover
    cover_img = Image.open(cover_path).convert("RGBA")
    front_coeffs = get_perspective_coeffs(front_dest, front_src)
    warped_front = cover_img.transform(canvas_size, Image.Transform.PERSPECTIVE, front_coeffs, Image.Resampling.BILINEAR)
    canvas.paste(warped_front, (0, 0), warped_front)
    
    # 4. Draw Neon outline around the box silhouette
    silhouette = [B, C, D, G, F, E]
    gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
    if color_palette:
        neon_color = color_palette[2]
    else:
        neon_color = gconfig["text_color"]
    draw_neon_outline(canvas, silhouette, neon_color)
    
    # Save as transparent PNG
    canvas.save(output_path, "PNG")
    print(f"3D Mockup generated: {output_path}")
    return output_path

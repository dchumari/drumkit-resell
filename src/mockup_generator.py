import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import GENRE_COLORS

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

def generate_spine(cover_path: str, height: int = 1200, width: int = 120, text: str = "ARQIVE COLLECTION", pack_type: str = "Default") -> Image.Image:
    """Generates a matching 2D spine strip from the cover art."""
    cover = Image.open(cover_path)
    
    # 1. Base spine texture cropped from the cover's left side
    spine = cover.crop((20, 0, 20 + width, height))
    # Apply a dark overlay gradient to give it depth
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 100))
    spine = Image.alpha_composite(spine.convert("RGBA"), overlay).convert("RGB")
    
    # 2. Draw Producer Icon (producer_icon_or_logo(1).png) at the top of vertical spine
    pi_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "producer_icon_or_logo(1).png")
    if os.path.exists(pi_path):
        try:
            pi_img = Image.open(pi_path).convert("RGBA")
            pi_img = pi_img.resize((48, 48), Image.Resampling.LANCZOS)
            # Center horizontally (width=120, so x = 60 - 24 = 36), 60px from top
            spine.paste(pi_img, (36, 60), pi_img)
        except Exception as e:
            print(f"Error drawing producer icon on spine: {e}")
            
    # 3. Draw vertical rotated text
    draw = ImageDraw.Draw(spine)
    try:
        font_spine = ImageFont.truetype("arialbd.ttf", 26)
        font_spine_badge = ImageFont.truetype("arialbd.ttf", 20)
    except IOError:
        font_spine = ImageFont.load_default()
        font_spine_badge = ImageFont.load_default()
        
    # Create horizontal text image for pack title
    bbox = draw.textbbox((0, 0), text, font=font_spine)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    txt_img = Image.new("RGBA", (tw + 40, th + 20), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt_img)
    td.text((20, 10), text, fill=(240, 240, 245, 220), font=font_spine)
    
    # Rotate 270 degrees (so it reads bottom-to-top)
    rotated_txt = txt_img.rotate(270, expand=True)
    
    # Center rotated text on spine (offset vertical center down a bit because of logo at top)
    rw, rh = rotated_txt.size
    sx = (width - rw) // 2
    sy = 150 + (height - 300 - rh) // 2
    spine.paste(rotated_txt, (sx, sy), rotated_txt)
    
    # 4. Draw rotated pack type label at the bottom of the spine
    badge_text = pack_type.upper()
    if badge_text == "LOOPKIT":
        badge_text = "LOOP KIT"
    elif badge_text == "ONE-SHOT":
        badge_text = "ONE-SHOTS"
    elif badge_text == "DEFAULT":
        badge_text = "SAMPLE PACK"
        
    badge_text = f"• {badge_text} •"
    bbox_b = draw.textbbox((0, 0), badge_text, font=font_spine_badge)
    bw, bh = bbox_b[2] - bbox_b[0], bbox_b[3] - bbox_b[1]
    
    badge_txt_img = Image.new("RGBA", (bw + 20, bh + 10), (0, 0, 0, 0))
    tbd = ImageDraw.Draw(badge_txt_img)
    # Draw with neon-ish light coloring matching text colors
    tbd.text((10, 5), badge_text, fill=(240, 240, 245, 180), font=font_spine_badge)
    rotated_badge = badge_txt_img.rotate(270, expand=True)
    
    rbw, rbh = rotated_badge.size
    bsx = (width - rbw) // 2
    bsy = height - 140
    spine.paste(rotated_badge, (bsx, bsy), rotated_badge)
    
    return spine

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
    spine_img = generate_spine(cover_path, height=1200, width=120, text=pack_name.upper(), pack_type=pack_type).convert("RGBA")
    spine_coeffs = get_perspective_coeffs(spine_dest, spine_src)
    warped_spine = spine_img.transform(canvas_size, Image.Transform.PERSPECTIVE, spine_coeffs, Image.Resampling.BILINEAR)
    canvas.paste(warped_spine, (0, 0), warped_spine)
    
    # 3. Warp Front Cover
    cover_img = Image.open(cover_path).convert("RGBA")
    front_coeffs = get_perspective_coeffs(front_dest, front_src)
    warped_front = cover_img.transform(canvas_size, Image.Transform.PERSPECTIVE, front_coeffs, Image.Resampling.BILINEAN if hasattr(Image.Resampling, 'BILINEAN') else Image.Resampling.BILINEAR)
    canvas.paste(warped_front, (0, 0), warped_front)
    
    # Save as transparent PNG
    canvas.save(output_path, "PNG")
    print(f"3D Mockup generated: {output_path}")
    return output_path

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

def generate_spine(cover_path: str, height: int = 1200, width: int = 120, text: str = "ARQIVE COLLECTION") -> Image.Image:
    """Generates a matching 2D spine strip from the cover art."""
    cover = Image.open(cover_path)
    
    # 1. Base spine texture cropped from the cover's left side
    spine = cover.crop((20, 0, 20 + width, height))
    # Apply a dark overlay gradient to give it depth
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 100))
    spine = Image.alpha_composite(spine.convert("RGBA"), overlay).convert("RGB")
    
    # 2. Draw vertical rotated text
    draw = ImageDraw.Draw(spine)
    try:
        font_spine = ImageFont.truetype("arialbd.ttf", 26)
    except IOError:
        font_spine = ImageFont.load_default()
        
    # Create horizontal text image
    bbox = draw.textbbox((0, 0), text, font=font_spine)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    txt_img = Image.new("RGBA", (tw + 40, th + 20), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt_img)
    td.text((20, 10), text, fill=(240, 240, 245, 220), font=font_spine)
    
    # Rotate 270 degrees (so it reads bottom-to-top)
    rotated_txt = txt_img.rotate(270, expand=True)
    
    # Center rotated text on spine
    rw, rh = rotated_txt.size
    sx = (width - rw) // 2
    sy = (height - rh) // 2
    
    spine.paste(rotated_txt, (sx, sy), rotated_txt)
    return spine

def generate_3d_mockup(cover_path: str, output_path: str, pack_name: str, genre: str):
    """Warps cover and spine into a 3D box mockup and saves it."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Get genre styles for top face color
    gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
    top_color = gconfig["bg_gradient"][0]  # Use base gradient color
    
    canvas_size = (1200, 1200)
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    
    # Define 3D perspectives coordinates
    # Spine (Left Face)
    spine_src = [(0, 0), (0, 1200), (120, 1200), (120, 0)]
    spine_dest = [(220, 330), (220, 970), (330, 1000), (330, 300)]
    
    # Front Cover Face
    front_src = [(0, 0), (0, 1200), (1200, 1200), (1200, 0)]
    front_dest = [(330, 300), (330, 1000), (830, 900), (830, 280)]
    
    # Top Face (Procedural color block)
    top_src = [(0, 0), (0, 300), (300, 300), (300, 0)]
    top_dest = [(220, 330), (330, 300), (830, 280), (720, 310)]
    
    # 1. Draw soft drop shadow behind the box
    shadow_canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_canvas)
    # Draw soft polygon shadow base
    sd.polygon([(210, 975), (320, 1010), (840, 910), (840, 895), (200, 955)], fill=(0, 0, 0, 120))
    shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=25))
    canvas.paste(shadow_canvas, (0, 0), shadow_canvas)
    
    # 2. Warp Spine Left Face
    spine_img = generate_spine(cover_path, height=1200, width=120, text=pack_name.upper())
    spine_coeffs = get_perspective_coeffs(spine_src, spine_dest)
    warped_spine = spine_img.transform(canvas_size, Image.Transform.PERSPECTIVE, spine_coeffs, Image.Resampling.BILINEAR)
    canvas.paste(warped_spine, (0, 0), warped_spine.convert("RGBA"))
    
    # 3. Warp Front Cover
    cover_img = Image.open(cover_path)
    front_coeffs = get_perspective_coeffs(front_src, front_dest)
    warped_front = cover_img.transform(canvas_size, Image.Transform.PERSPECTIVE, front_coeffs, Image.Resampling.BILINEAR)
    canvas.paste(warped_front, (0, 0), warped_front.convert("RGBA"))
    
    # 4. Warp Top Face
    # Create top face color solid matching the theme
    top_img = Image.new("RGB", (300, 300), top_color)
    top_draw = ImageDraw.Draw(top_img)
    # Add minor highlight lines to the top face
    top_draw.line([(0, 0), (300, 300)], fill=(top_color[0]+30, top_color[1]+30, top_color[2]+30), width=3)
    top_coeffs = get_perspective_coeffs(top_src, top_dest)
    warped_top = top_img.transform(canvas_size, Image.Transform.PERSPECTIVE, top_coeffs, Image.Resampling.BILINEAR)
    canvas.paste(warped_top, (0, 0), warped_top.convert("RGBA"))
    
    # Save as transparent PNG
    canvas.save(output_path, "PNG")
    print(f"3D Mockup generated: {output_path}")
    return output_path

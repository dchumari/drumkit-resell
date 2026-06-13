from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, random, os

SIZE = 1200
BG = (10, 8, 14)
LAVA_GLOW = (255, 100, 20)
LAVA_BRIGHT = (255, 180, 40)
RIDGE = (25, 20, 30)
TOPO = (60, 50, 70)
STARDUST = (180, 170, 200)
GLOW_INNER = (255, 160, 30)
GLOW_OUTER = (255, 80, 10)
BRAND_COLOR = (160, 150, 170)

img = Image.new("RGB", (SIZE, SIZE), BG)
draw = ImageDraw.Draw(img)
random.seed(42)

try:
    font_brand = ImageFont.truetype("arial.ttf", 14)
    font_trap = ImageFont.truetype("arialbd.ttf", 220)
except IOError:
    try:
        font_brand = ImageFont.truetype("arial.ttf", 14)
        font_trap = ImageFont.truetype("arial.ttf", 220)
    except IOError:
        font_brand = ImageFont.load_default()
        font_trap = ImageFont.load_default()

# noise texture
for _ in range(60000):
    x, y = random.randint(0, SIZE - 1), random.randint(0, SIZE - 1)
    v = random.randint(0, 22)
    r, g, b = img.getpixel((x, y))
    img.putpixel((x, y), (min(255, r + v), min(255, g + v), min(255, b + v)))

# stardust
for _ in range(500):
    x, y = random.randint(0, SIZE - 1), random.randint(0, SIZE - 1)
    r = random.randint(1, 3)
    a = random.randint(40, 160)
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                px, py = x + dx, y + dy
                if 0 <= px < SIZE and 0 <= py < SIZE:
                    o = img.getpixel((px, py))
                    img.putpixel((px, py), tuple(int(o[i] + (STARDUST[i] - o[i]) * a / 255) for i in range(3)))

# mountain ridges
for layer in range(8):
    yb = SIZE * 0.55 + layer * 35
    amp = 60 + layer * 25
    c = tuple(int(RIDGE[i] + (35 - layer * 4)) for i in range(3))
    pts = []
    for i in range(80):
        x = int(i * SIZE / 79)
        y = int(yb + amp * math.sin(i * 0.3 + random.random() * 0.4) +
                amp * 0.5 * math.sin(i * 0.7 + 1.5) +
                amp * 0.25 * math.sin(i * 1.3 + 3.0))
        pts.append((x, y))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=c, width=2 + layer)

# lava glow layers
for layer in range(5):
    lava = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lava)
    yb = SIZE * 0.58 + layer * 30
    amp = 50 + layer * 20
    pts = []
    for i in range(100):
        x = int(i * SIZE / 99)
        y = int(yb + amp * math.sin(i * 0.35 + layer * 0.8) +
                amp * 0.6 * math.sin(i * 0.65 + 2.0 + layer) +
                amp * 0.3 * math.sin(i * 1.1 + 4.0 + layer * 0.5))
        pts.append((x, y))
    for i in range(len(pts) - 1):
        ld.line([pts[i], pts[i + 1]], fill=(*LAVA_GLOW, 55 - layer * 9), width=8 + layer * 3)
    img = Image.alpha_composite(img.convert("RGBA"), lava).convert("RGB")

# bright lava spots
for _ in range(35):
    x = random.randint(50, SIZE - 50)
    y = random.randint(int(SIZE * 0.5), int(SIZE * 0.85))
    r = random.randint(3, 12)
    a = random.randint(60, 180)
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([x - r, y - r, x + r, y + r], fill=(*LAVA_BRIGHT, a))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=r * 1.5))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

# topographic lines (upper)
for layer in range(12):
    topo = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    td = ImageDraw.Draw(topo)
    yb = SIZE * 0.45 + layer * 18
    amp = 30 + layer * 8
    pts = []
    for i in range(120):
        x = int(i * SIZE / 119)
        y = int(yb + amp * math.sin(i * 0.25 + layer * 0.6) +
                amp * 0.7 * math.sin(i * 0.5 + 1.8 + layer * 0.4) +
                amp * 0.4 * math.sin(i * 0.9 + 3.5 + layer * 0.3))
        pts.append((x, y))
    for i in range(len(pts) - 1):
        td.line([pts[i], pts[i + 1]], fill=(*TOPO, 50), width=1)
    img = Image.alpha_composite(img.convert("RGBA"), topo).convert("RGB")

# topographic lines (lower)
for layer in range(8):
    topo = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    td = ImageDraw.Draw(topo)
    yb = SIZE * 0.7 + layer * 20
    amp = 25 + layer * 6
    pts = []
    for i in range(120):
        x = int(i * SIZE / 119)
        y = int(yb + amp * math.sin(i * 0.3 + layer * 0.7) +
                amp * 0.6 * math.sin(i * 0.55 + 2.5 + layer * 0.5))
        pts.append((x, y))
    for i in range(len(pts) - 1):
        td.line([pts[i], pts[i + 1]], fill=(*TOPO, 45), width=1)
    img = Image.alpha_composite(img.convert("RGBA"), topo).convert("RGB")

draw = ImageDraw.Draw(img)

# 3D block text "TRAP" - shadow layers
cx, cy = SIZE // 2, SIZE // 2
text = "TRAP"
for depth in range(15, 0, -1):
    ox = depth * 2
    oy = depth * 2
    shade = int(20 + depth * 3)
    bbox = draw.textbbox((0, 0), text, font=font_trap)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = cx - tw // 2 + ox
    ty = cy - th // 2 + oy
    draw.text((tx, ty), text, fill=(shade, shade - 5, shade + 5), font=font_trap)

# main white text
bbox = draw.textbbox((0, 0), text, font=font_trap)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
tx = cx - tw // 2
ty = cy - th // 2
draw.text((tx, ty), text, fill=(240, 240, 245), font=font_trap)

# inner neon glow - overlay golden-orange
glow_text = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow_text)
gd.text((tx, ty), text, fill=(*GLOW_INNER, 200), font=font_trap)
glow_text = glow_text.filter(ImageFilter.GaussianBlur(radius=6))

glow_outer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
god = ImageDraw.Draw(glow_outer)
god.text((tx, ty), text, fill=(*GLOW_OUTER, 120), font=font_trap)
glow_outer = glow_outer.filter(ImageFilter.GaussianBlur(radius=18))

img = Image.alpha_composite(img.convert("RGBA"), glow_outer).convert("RGB")
img = Image.alpha_composite(img.convert("RGBA"), glow_text).convert("RGB")

# redraw crisp white text on top
draw = ImageDraw.Draw(img)
draw.text((tx, ty), text, fill=(245, 245, 250), font=font_trap)

# brand text top
brand_top = "DRUMKIT ARCHIVE"
bbox = draw.textbbox((0, 0), brand_top, font=font_brand)
bw = bbox[2] - bbox[0]
draw.text((cx - bw // 2, 18), brand_top, fill=BRAND_COLOR, font=font_brand)

# brand text bottom
brand_bot = "PREMIUM SAMPLE PACK"
bbox = draw.textbbox((0, 0), brand_bot, font=font_brand)
bw = bbox[2] - bbox[0]
draw.text((cx - bw // 2, SIZE - 36), brand_bot, fill=BRAND_COLOR, font=font_brand)

# subtle border
draw.rectangle([4, 4, SIZE - 5, SIZE - 5], outline=(40, 35, 50), width=2)

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trap_cover.png")
img.save(out_path)
print(f"Saved: {out_path}")

import os
import re
import random
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Tuple, Dict, Optional
from config import GENRE_COLORS, ASSETS_DIR, MULTIPLE_STYLES
from cover_generator import generate_gradient
from font_manager import get_font


def get_wav_duration(filepath: str) -> float:
    """Attempts to read the duration of an audio file using wave first, then ffprobe fallback."""
    import wave
    try:
        with wave.open(filepath, 'rb') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            return frames / float(rate)
    except Exception:
        try:
            import json
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", filepath]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            return float(data["format"]["duration"])
        except Exception:
            return 2.5

def compile_preview_audio(showcase_files: List[Tuple[str, str]], output_audio_path: str, voice_tag_path: str) -> Tuple[str, List[dict]]:
    """
    Trims, concatenates, and mixes voice tag watermarks into the showcase audio.
    Standardizes each audio segment first to temporary WAV files to prevent command length limits and mixed sample rate issues.
    Returns (output_audio_path, markers)
    """
    import config
    temp_dir = os.path.join(os.path.dirname(output_audio_path), "temp_concat_parts")
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_concat = os.path.join(os.path.dirname(output_audio_path), "temp_concat.wav")
    if os.path.exists(temp_concat):
        try:
            os.remove(temp_concat)
        except Exception:
            pass
        
    current_time = 0.0
    markers = []
    temp_part_files = []
    
    # 1. Pre-process each segment individually (trim, pad, and standardize to 44.1kHz stereo WAV)
    for idx, (fpath, cat) in enumerate(showcase_files):
        actual_dur = get_wav_duration(fpath)
        
        cat_caps = cat.upper()
        if "LOOP" in cat_caps or cat_caps == "808S" or actual_dur >= 5.0:
            duration = min(actual_dur, getattr(config, "PREVIEW_LOOP_DURATION", 12.0))
        else:
            min_dur = getattr(config, "PREVIEW_ONESHOT_MIN_DURATION", 1.0)
            max_dur = getattr(config, "PREVIEW_ONESHOT_MAX_DURATION", 2.5)
            if actual_dur < min_dur:
                duration = min_dur
            else:
                duration = min(actual_dur, max_dur)
                
        # Limit total showcase preview time to 3 minutes (180.0 seconds)
        if current_time + duration > 180.0:
            print(f"Reached 3-minute showcase duration limit. Skipping remaining {len(showcase_files) - idx} files.")
            break
            
        part_wav = os.path.join(temp_dir, f"part_{idx:03d}.wav")
        # Standardize sample rate (44100), channels (2), codec (pcm_s16le)
        cmd_part = [
            "ffmpeg", "-y", "-i", fpath,
            "-af", f"apad,atrim=end={duration},asetpts=PTS-STARTPTS",
            "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", part_wav
        ]
        try:
            subprocess.run(cmd_part, check=True, capture_output=True, text=True)
            temp_part_files.append(part_wav)
        except subprocess.CalledProcessError as e:
            print(f"Error standardizing showcase audio segment {fpath}: exit status {e.returncode}")
            print(f"FFmpeg stdout: {e.stdout}")
            print(f"FFmpeg stderr: {e.stderr}")
            continue
        except Exception as e:
            print(f"Error standardizing showcase audio segment {fpath}: {e}")
            continue
            
        fname = os.path.basename(fpath)
        display_name = fname
        for prefix in ["[AQ]", "[AQ] "]:
            if display_name.startswith(prefix):
                display_name = display_name[len(prefix):]
                
        for suffix in [".wav", ".mp3", ".aif", ".aiff", ".flac"]:
            if display_name.lower().endswith(suffix):
                display_name = display_name[:-len(suffix)]
                
        display_name = re_strip_meta(display_name)
        
        markers.append({
            "name": display_name,
            "category": cat,
            "start": current_time,
            "end": current_time + duration,
            "duration": duration
        })
        current_time += duration

    if not temp_part_files:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        return output_audio_path, []

    # 2. Write the concat list txt file
    concat_txt_path = os.path.join(temp_dir, "concat_list.txt")
    os.makedirs(temp_dir, exist_ok=True)  # guard: recreate if deleted by cleanup race
    with open(concat_txt_path, "w", encoding="utf-8") as f:
        for p in temp_part_files:
            # Format filename properly for FFmpeg concat demuxer (escaping single quotes)
            safe_p = os.path.abspath(p).replace("'", "'\\''")
            f.write(f"file '{safe_p}'\n")
            
    # 3. Concatenate using FFmpeg demuxer
    cmd_concat = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt_path, "-c", "copy", temp_concat]
    
    try:
        subprocess.run(cmd_concat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error concatenating showcase audio via demuxer: {e}")
        # Clean up and fallback
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        if len(showcase_files) > 0:
            shutil.copy(showcase_files[0][0], output_audio_path)
        return output_audio_path, markers

    # 4. Mix in the voice tag watermarks
    tag_inputs = ["-i", temp_concat]
    if voice_tag_path and os.path.exists(voice_tag_path):
        tag_inputs.extend(["-i", voice_tag_path])
        delay_filters = []
        mix_inputs = ["[0:a]"]
        
        interval = 25.0
        current_delay = 10.0
        tag_idx = 1
        while current_delay < current_time:
            delay_ms = int(current_delay * 1000)
            delay_filters.append(f"[1:a]adelay={delay_ms}|{delay_ms}[vtag{tag_idx}]")
            mix_inputs.append(f"[vtag{tag_idx}]")
            current_delay += interval
            tag_idx += 1
            
        if delay_filters:
            filter_complex = "; ".join(delay_filters) + "; " + "".join(mix_inputs) + f"amix=inputs={tag_idx}:weights=1 " + " ".join(["0.25"] * (tag_idx - 1)) + "[aout]"
            cmd_mix = ["ffmpeg", "-y"] + tag_inputs + ["-filter_complex", filter_complex, "-map", "[aout]", "-ar", "44100", "-b:a", "320k", output_audio_path]
        else:
            cmd_mix = ["ffmpeg", "-y", "-i", temp_concat, "-ar", "44100", "-b:a", "320k", output_audio_path]
    else:
        cmd_mix = ["ffmpeg", "-y", "-i", temp_concat, "-ar", "44100", "-b:a", "320k", output_audio_path]

    try:
        subprocess.run(cmd_mix, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error mixing voice tags: {e}")
        shutil.copy(temp_concat, output_audio_path)
    finally:
        # Clean up all temporary files
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        if os.path.exists(temp_concat):
            try:
                os.remove(temp_concat)
            except Exception:
                pass
            
    return output_audio_path, markers

def re_strip_meta(text: str) -> str:
    """Removes trailing bracket metadata."""
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    return text.strip()

def format_time_srt(seconds: float) -> str:
    """Formats seconds into SRT time format: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def create_srt_file(markers: List[dict], srt_path: str):
    """Generates an SRT subtitle file (left empty since subtitle burn-in is removed)."""
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("")

def generate_capsule_image(color: Tuple[int, int, int], output_path: str, width: int = 480, height: int = 28, style: Optional[str] = None):
    """Creates a colored capsule/box image to highlight active track in overlay matching the selected style."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    if style == "neon_sunset":
        # Cyberpunk sharp box with double outline/bright neon border
        draw.rectangle([0, 0, width, height], fill=(*color, 35), outline=(*color, 255), width=2)
    elif style == "pastel_minimalist":
        # Flat solid colored highlight bar, no border
        draw.rectangle([0, 0, width, height], fill=(*color, 90))
    else:
        # Standard rounded pill
        r = height // 2
        draw.rounded_rectangle([0, 0, width, height], radius=r, fill=(*color, 45), outline=(*color, 240), width=1)
        
    img.save(output_path, "PNG")


def create_tracklist_overlay(pack_name: str, genre: str, markers: List[dict], output_img_path: str, color_palette=None, style: Optional[str] = None) -> List[dict]:
    """
    Generates a transparent 1920x1080 PNG image with a tracklist overlay on the left.
    Each visual style (--style) has a completely unique layout, geometry, typography, and decoration.
    Returns tracking coordinates of each listed sample item for FFmpeg highlight overlays.
    """
    img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 1. Resolve style configurations
    style_key = style if (style and style in MULTIPLE_STYLES) else "Default"
    
    # Style layout metadata: (font_family, bullet_str, bullet_x, text_x, logo_x, logo_y, badge_x)
    style_layouts = {
        "rounded_sidebar":  ("Mulish", "• ", 80, 105, 60, 100, 60),
        "neon_sunset":      ("Geist", ">> ", 90, 125, 80, 80, 80),
        "pastel_minimalist":("OpenSans", "", 90, 90, 90, 90, 90),
        "friendly_glass":   ("Nunito", "● ", 90, 115, 80, 80, 80),
        "liquid_glass":     ("Roboto", "♦ ", 90, 115, 80, 80, 80),
        "floating_badge":   ("Nunito", "○ ", 90, 115, 80, 80, 80),
        "frosted_bubble":   ("Mulish", "○ ", 90, 115, 80, 80, 80),
        "liquid_sunset":    ("Nunito", "• ", 80, 105, 70, 90, 70),
        "asymmetric_float": ("Geist", "- ", 100, 122, 90, 90, 90),
        "Default":          ("Nunito", "• ", 90, 115, 80, 80, 80)
    }
    
    font_family, bullet_str, bullet_x, text_x, logo_x, logo_y, badge_x = style_layouts.get(style_key, style_layouts["Default"])
    
    # Resolve color schemes
    if style and style in MULTIPLE_STYLES:
        sconfig = MULTIPLE_STYLES[style]
        card_opacity = sconfig["card_opacity"]
        rounded_corners = sconfig["rounded_corners"]
    else:
        card_opacity = 170
        rounded_corners = 16
        
    if color_palette:
        color1, color2, text_color = color_palette
        border_color = text_color
    else:
        if style and style in MULTIPLE_STYLES:
            sconfig = MULTIPLE_STYLES[style]
            color1, color2 = sconfig["bg_gradient"]
            text_color = sconfig["text_color"]
            border_color = sconfig["border_color"]
        else:
            gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
            color1, color2 = gconfig["bg_gradient"]
            text_color = gconfig["text_color"]
            border_color = gconfig["border_color"]

    # Load premium local fonts
    font_logo = get_font(font_family, 36, is_bold=True)
    font_sub = get_font(font_family, 20)
    font_header = get_font(font_family, 26, is_bold=True)
    font_item = get_font(font_family, 22)
    font_badge = get_font(font_family, 15, is_bold=True)

    # 2. Draw styled backing cards
    card_box = [50, 50, 550, 1030]
    w = card_box[2] - card_box[0]
    h = card_box[3] - card_box[1]
    
    if style_key == "rounded_sidebar":
        # Full height sidebar spanning edge-to-edge on the left
        sidebar_box = [0, 0, 440, 1080]
        draw.rectangle(sidebar_box, fill=(*color1, 230))
        draw.line([(439, 0), (439, 1080)], fill=(*border_color, 120), width=1)
        
        # Mac-style control dots
        dot_y = 50
        draw.ellipse([60, dot_y, 70, dot_y + 10], fill=(255, 95, 86, 255))
        draw.ellipse([76, dot_y, 86, dot_y + 10], fill=(255, 189, 46, 255))
        draw.ellipse([92, dot_y, 102, dot_y + 10], fill=(39, 201, 63, 255))
        
    elif style_key == "pastel_minimalist":
        # Swiss style: no backing card background, just a thick vertical accent bar
        draw.line([(70, 50), (70, 1030)], fill=border_color, width=4)
        # Decorative quotes block
        font_quote = get_font("Georgia", 64, is_bold=True)
        draw.text((90, 40), "“", fill=(*text_color, 150), font=font_quote)
        
    elif style_key == "neon_sunset":
        # Cyberpunk glowing wireframe box with gridlines
        # Grid lines background
        for grid_y in range(50 + 40, 1030, 80):
            draw.line([(50, grid_y), (550, grid_y)], fill=(*border_color, 25), width=1)
        for grid_x in range(50 + 50, 550, 100):
            draw.line([(grid_x, 50), (grid_x, 1030)], fill=(*border_color, 25), width=1)
            
        # Draw neon glow outline effect
        for w_glow in [6, 4, 2]:
            alpha_glow = 255 if w_glow == 2 else (60 if w_glow == 4 else 25)
            draw.rectangle([50 - w_glow//2, 50 - w_glow//2, 550 + w_glow//2, 1030 + w_glow//2], outline=(*border_color, alpha_glow), width=1)
            
    elif style_key == "friendly_glass":
        # Large bubble/rounded corners card with decorative dots
        draw.rounded_rectangle(card_box, radius=32, fill=(*color1, 85), outline=(*border_color, 160), width=3)
        # Floating corner bubbles
        draw.ellipse([500, 70, 515, 85], fill=(*border_color, 180))
        draw.ellipse([480, 75, 490, 85], fill=(*border_color, 100))
        
    elif style_key == "liquid_glass":
        # Asymmetric corner card (top-left & bottom-right fully rounded, others sharp)
        mask = Image.new("L", (w, h), 0)
        m_draw = ImageDraw.Draw(mask)
        r = 45
        m_draw.rectangle([r, 0, w, h], fill=255)
        m_draw.rectangle([0, r, w, h - r], fill=255)
        m_draw.pieslice([0, 0, r * 2, r * 2], 180, 270, fill=255)
        m_draw.pieslice([w - r * 2, h - r * 2, w, h], 0, 90, fill=255)
        
        card_canvas = Image.new("RGBA", (w, h), (*color1, 90))
        cc_draw = ImageDraw.Draw(card_canvas)
        cc_draw.rectangle([r, 0, w - 1, h - 1], outline=(*border_color, 150), width=2)
        cc_draw.rectangle([0, r, w - 1, h - r], outline=(*border_color, 150), width=2)
        cc_draw.arc([0, 0, r * 2, r * 2], 180, 270, fill=(*border_color, 150), width=2)
        cc_draw.arc([w - r * 2, h - r * 2, w, h], 0, 90, fill=(*border_color, 150), width=2)
        
        card_final = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        card_final.paste(card_canvas, (0, 0), mask=mask)
        img.paste(card_final, (50, 50), card_final)
        
        # Inner liquid offset divider
        draw.rounded_rectangle([56, 56, 544, 1024], radius=30, fill=(0, 0, 0, 0), outline=(255, 255, 255, 30), width=1)
        
    elif style_key == "floating_badge":
        # Split floating card layout (Title card at top, Tracklist below)
        draw.rounded_rectangle([50, 50, 550, 220], radius=16, fill=(*color1, 80), outline=(*border_color, 160), width=2)
        draw.rounded_rectangle([50, 245, 550, 1030], radius=16, fill=(*color1, 80), outline=(*border_color, 160), width=2)
        
    elif style_key == "frosted_bubble":
        # Frosty white backing card with bubble graphics
        draw.rounded_rectangle(card_box, radius=30, fill=(255, 255, 255, 55), outline=(255, 255, 255, 150), width=2)
        draw.ellipse([510, 80, 526, 96], fill=(255, 255, 255, 70))
        draw.ellipse([515, 110, 523, 118], fill=(255, 255, 255, 90))
        
    elif style_key == "liquid_sunset":
        # Warm sidebar with slanted dividing separator
        draw.rectangle([30, 0, 510, 1080], fill=(*color1, 220), outline=(*border_color, 120), width=1)
        draw.line([(30, 210), (510, 230)], fill=(*border_color, 180), width=2)
        
    elif style_key == "asymmetric_float":
        # Offset card box with double outline offset borders
        draw.rounded_rectangle([70, 70, 570, 1010], radius=24, fill=(*color1, 80), outline=(*border_color, 120), width=2)
        draw.rounded_rectangle([65, 65, 575, 1015], radius=26, fill=(0,0,0,0), outline=(*border_color, 50), width=1)
        
    else:
        # Standard Fallback Glassmorphic Card
        draw.rounded_rectangle(card_box, radius=16, fill=(*color1, 80), outline=(*border_color, 120), width=2)

    # 3. Draw Branding Titles
    actual_logo_y = logo_y
    if style_key == "pastel_minimalist":
        actual_logo_y = 120
        
    if style_key != "floating_badge" and style_key != "pastel_minimalist":
        draw.text((logo_x, actual_logo_y), "ARQIVE ARCHIVE", fill=(255, 255, 255, 250), font=font_logo)
        draw.text((logo_x, actual_logo_y + 45), f"PREMIUM {genre.upper()} SELECTION", fill=text_color, font=font_sub)
        draw.line([(logo_x, actual_logo_y + 80), (logo_x + 400, actual_logo_y + 80)], fill=(255, 255, 255, 30), width=1)
        header_y = actual_logo_y + 105
    elif style_key == "pastel_minimalist":
        draw.text((logo_x, actual_logo_y), "ARQIVE PREMIUM", fill=(255, 255, 255, 255), font=font_logo)
        draw.text((logo_x, actual_logo_y + 45), f"DAWN 94 {genre.upper()} PACK", fill=(255, 255, 255, 200), font=font_sub)
        draw.line([(logo_x, actual_logo_y + 80), (logo_x + 400, actual_logo_y + 80)], fill=(255, 255, 255, 60), width=2)
        header_y = actual_logo_y + 105
    else:
        # floating_badge
        draw.text((logo_x, actual_logo_y), pack_name.upper()[:24], fill=(255, 255, 255, 240), font=font_logo)
        draw.text((logo_x, actual_logo_y + 45), f"PREMIUM TRAP SELECTION", fill=text_color, font=font_sub)
        draw.line([(logo_x, actual_logo_y + 80), (logo_x + 400, actual_logo_y + 80)], fill=(255, 255, 255, 30), width=1)
        header_y = actual_logo_y + 105

    draw.text((logo_x, header_y), "KIT SHOWCASE:", fill=(255, 255, 255) if style_key == "pastel_minimalist" else text_color, font=font_header)
    
    # 4. Draw Tracklist Items
    y = header_y + 45
    categories_seen = []
    positions = []
    
    for idx, m in enumerate(markers):
        is_new_cat = (m["category"] not in categories_seen)
        needed_h = 32
        if is_new_cat:
            needed_h += 36 + 12
            
        if y + needed_h > 970:
            positions.append({
                "name": "...more",
                "y": y - 2,
                "is_more": True
            })
            draw.text((text_x, y), "...more", fill=(180, 180, 180, 150) if style_key != "pastel_minimalist" else (255, 255, 255, 150), font=font_item)
            break
            
        if is_new_cat:
            categories_seen.append(m["category"])
            cat_text = m['category'].upper()
            try:
                bbox = draw.textbbox((0, 0), cat_text, font=font_badge)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            except Exception:
                tw, th = len(cat_text) * 8, 15
            
            pad_x = 12
            pad_y = 6
            badge_w = tw + 2 * pad_x
            badge_h = th + 2 * pad_y
            
            # Badge placement
            badge_y = y
            
            # Badge background style
            if style_key == "pastel_minimalist":
                draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=4, fill=(*text_color, 255))
                badge_fg_color = (255, 255, 255)
            elif style_key == "neon_sunset":
                # Transparent neon outline badge
                draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=4, fill=(0, 0, 0, 100), outline=text_color, width=1)
                badge_fg_color = text_color
            else:
                draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=4, fill=text_color)
                badge_fg_color = (10, 10, 15)
                
            text_badge_x = badge_x + pad_x - bbox[0]
            text_badge_y = badge_y + pad_y - bbox[1]
            draw.text((text_badge_x, text_badge_y), cat_text, fill=badge_fg_color, font=font_badge)
            y += badge_h + 12
            
        positions.append({
            "name": m["name"],
            "y": y - 2,
            "is_more": False
        })
        
        # Tracklist text item color
        if style_key == "pastel_minimalist":
            item_color = (255, 255, 255, 240)
        else:
            item_color = (240, 240, 245, 220)
            
        # Draw bullet and name separately for styling control
        if bullet_str:
            draw.text((bullet_x, y), bullet_str, fill=text_color, font=font_item)
        draw.text((text_x, y), m['name'][:28], fill=item_color, font=font_item)
        y += 32
        
    if output_img_path:
        img.save(output_img_path, "PNG")
        print(f"Tracklist overlay image created: {output_img_path} with style: {style_key}")
    return positions

def hex_to_ffmpeg_color(rgb: tuple) -> str:
    """Converts (R,G,B) tuple to FFmpeg color string like 0xRRGGBB."""
    return f"0x{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

def generate_ffmpeg_tint_filter(tint_color: str, size: str = "1920x1080") -> str:
    """Builds greyscale conversion followed by color tint overlay blend."""
    return f"format=gray,eq=brightness=-0.30,split[g1][g2];color=c={tint_color}:s={size}[tc];[g1][tc]blend=all_mode='multiply':all_opacity=0.5[tinted];[tinted][g2]blend=all_mode='overlay':all_opacity=0.4"

def build_capsule_scroll_expression(markers: List[dict], positions: List[dict]) -> str:
    """
    Builds a nested conditional FFmpeg math expression for dynamic scroll highlight.
    Returns an expression mapping current time 't' to the target Y-coordinate.
    """
    expr = ""
    more_y = 1000
    for pos in positions:
        if pos.get("is_more"):
            more_y = pos["y"]
            break
            
    for idx, m in enumerate(markers):
        y_val = more_y
        for pos in positions:
            if not pos.get("is_more") and pos["name"] == m["name"]:
                y_val = pos["y"]
                break
                
        if idx == len(markers) - 1:
            expr += f"{y_val}"
        else:
            next_m = markers[idx + 1]
            next_y = more_y
            for pos in positions:
                if not pos.get("is_more") and pos["name"] == next_m["name"]:
                    next_y = pos["y"]
                    break
            
            trans_start = m["end"] - 0.5
            trans_end = m["end"]
            
            cond_expr = (
                f"if(lt(t,{trans_start}),{y_val},"
                f"if(lt(t,{trans_end}),{y_val}+({next_y}-{y_val})*(t-{trans_start})/0.5,{next_y}))"
            )
            expr += f"if(lt(t,{m['end']}),{cond_expr},"
            
    expr += ")" * (len(markers) - 1)
    return expr

def get_pexels_background_video(cache_dir: str = "assets/cache", registry_path: str = "data/used_background_videos.json") -> Optional[str]:
    """
    Queries Pexels Videos search API for 'abstract background',
    filters out previously used video IDs using the registry,
    downloads the selected HD video, and saves the ID to the registry.
    """
    import config
    api_key = getattr(config, "PEXELS_API_KEY", "")
    if not api_key:
        return None
        
    import json
    import urllib.parse
    import urllib.request
    import random
    import hashlib
    
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    # 1. Load used videos registry
    used_ids = set()
    if os.path.exists(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                used_ids = set(json.load(f))
        except Exception:
            pass
            
    # 2. Query Pexels Video API
    query = "abstract background"
    url = f"https://api.pexels.com/v1/videos/search?query={urllib.parse.quote(query)}&per_page=80"
    
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        print(f"Searching Pexels Video API for: '{query}'...")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            videos = data.get("videos", [])
            
        if not videos:
            print("No Pexels videos found.")
            return None
            
        # 3. Filter out already used video IDs
        candidates = [v for v in videos if v.get("id") not in used_ids]
        
        # If all videos in page were already used, reset registry to avoid blocking
        if not candidates:
            print("All returned Pexels videos were already used. Resetting used videos list to recycle.")
            candidates = videos
            used_ids = set()
            
        # Select a random unused video
        selected_video = random.choice(candidates)
        video_id = selected_video["id"]
        
        # 4. Find best MP4 video file by resolution (preferring Full HD/HD up to 1920px)
        video_files = selected_video.get("video_files", [])
        mp4_files = [vf for vf in video_files if vf.get("file_type") == "video/mp4" and vf.get("link")]
        best_file = None
        if mp4_files:
            # Filter to files with both width and height <= 1920 to keep processing extremely lightweight
            lightweight_files = [vf for vf in mp4_files if (vf.get("width") or 0) <= 1920 and (vf.get("height") or 0) <= 1920]
            if lightweight_files:
                # Sort to find the file closest to Full HD (1920) or HD (1280)
                lightweight_files.sort(key=lambda x: abs((x.get("width") or 0) - 1920))
                best_file = lightweight_files[0]
            else:
                # Fallback to the smallest available file if all are larger than 1920
                mp4_files.sort(key=lambda x: (x.get("width") or 0) * (x.get("height") or 0))
                best_file = mp4_files[0]

            
        if not best_file or not best_file.get("link"):
            print("No valid video link found in Pexels payload.")
            return None
            
        # 5. Download the video file
        download_url = best_file["link"]
        cached_video_path = os.path.join(cache_dir, f"video_{video_id}.mp4")
        
        if not os.path.exists(cached_video_path):
            img_req = urllib.request.Request(download_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            print(f"Downloading Pexels video background: {download_url}")
            with urllib.request.urlopen(img_req, timeout=15) as img_resp:
                with open(cached_video_path, "wb") as out_file:
                    out_file.write(img_resp.read())
                    
        # 6. Save selection to registry
        used_ids.add(video_id)
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(list(used_ids), f, indent=4)
            
        print(f"Successfully selected and cached Pexels video background (ID: {video_id})")
        return cached_video_path
    except Exception as e:
        print(f"Pexels Video API failed: {e}. Falling back to default background.")
        return None

def compile_video_16_9(audio_path: str, mockup_path: str, overlay_path: str, output_video_path: str, genre: str, markers: List[dict], srt_path: str, color_palette=None, pexels_video_path: Optional[str] = None, style: Optional[str] = None) -> bool:
    """
    Compiles the 16:9 landscape YouTube showcase video.
    Features dynamically colored tinted background loop and scrolling active track highlight.
    """
    if color_palette:
        color1, color2, text_color_rgb = color_palette
        wave_color = hex_to_ffmpeg_color(text_color_rgb)
        capsule_color = text_color_rgb
    elif style and style in MULTIPLE_STYLES:
        sconfig = MULTIPLE_STYLES[style]
        color1, color2 = sconfig["bg_gradient"]
        text_color_rgb = sconfig["text_color"]
        wave_color = sconfig["wave_color"]
        capsule_color = sconfig["active_badge_bg"]
        color_palette = (color1, color2, text_color_rgb)
    else:
        gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
        color1, color2 = gconfig["bg_gradient"]
        text_color_rgb = gconfig["text_color"]
        wave_color = hex_to_ffmpeg_color(text_color_rgb)
        capsule_color = text_color_rgb
        color_palette = (color1, color2, text_color_rgb)
        
    tint_color = hex_to_ffmpeg_color(color1)
    
    # Dynamic capsule highlight geometry depending on visual style layout
    capsule_geometries = {
        "rounded_sidebar":  (20, 400),
        "neon_sunset":      (70, 460),
        "pastel_minimalist":(75, 430),
        "friendly_glass":   (70, 460),
        "liquid_glass":     (70, 460),
        "floating_badge":   (70, 460),
        "frosted_bubble":   (70, 460),
        "liquid_sunset":    (50, 440),
        "asymmetric_float": (90, 440),
        "Default":          (70, 460)
    }
    
    style_key = style if (style and style in MULTIPLE_STYLES) else "Default"
    capsule_x, capsule_width = capsule_geometries.get(style_key, capsule_geometries["Default"])
    
    # 1. Generate Highlight capsule PNG
    capsule_path = os.path.join(os.path.dirname(output_video_path), "temp_capsule.png")
    generate_capsule_image(capsule_color, capsule_path, width=capsule_width, height=28, style=style)
    
    # 2. Get layout overlay positions (passing None for path to avoid overwriting overlay)
    positions = create_tracklist_overlay("Dummy", genre, markers, None, color_palette, style=style)
    
    # Find background video (Try passed Pexels video first, then fetch Pexels, then local assets, then gradient fallback)
    pexels_video = pexels_video_path if pexels_video_path and os.path.exists(pexels_video_path) else get_pexels_background_video()
    temp_bg_gradient = None
    
    if pexels_video:
        bg_video_path = pexels_video
        bg_input = f"-stream_loop -1 -i {bg_video_path}"
        bg_filter = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,{generate_ffmpeg_tint_filter(tint_color, '1920x1080')}"
    else:
        bg_video = "bg_loop_1.mp4"
        if os.path.exists(ASSETS_DIR):
            loops = [f for f in os.listdir(ASSETS_DIR) if f.startswith("bg_loop") and f.endswith(".mp4")]
            if loops:
                bg_video = random.choice(loops)
        bg_video_path = os.path.join(ASSETS_DIR, bg_video)
        
        if not os.path.exists(bg_video_path):
            temp_bg_gradient = os.path.join(os.path.dirname(output_video_path), "temp_bg_gradient.png")
            gradient_img = generate_gradient(2000, 2000, color1, color2)
            gradient_img.save(temp_bg_gradient, "PNG")
            bg_input = f"-loop 1 -i {temp_bg_gradient}"
            bg_filter = "crop=w=1920:h=1080:x='(in_w-1920)/2 + (in_w-1920)/2*sin(t*0.1)':y='(in_h-1080)/2 + (in_h-1080)/2*cos(t*0.1)',setsar=1"
        else:
            bg_input = f"-stream_loop -1 -i {bg_video_path}"
            bg_filter = f"scale=1920:1080,{generate_ffmpeg_tint_filter(tint_color, '1920x1080')}"
 
    if not markers:
        print("Error: No markers provided for video compilation.")
        return False
    total_duration = markers[-1]["end"]
    
    scroll_expr = build_capsule_scroll_expression(markers, positions)
    
    filter_complex = (
        f"[0:v]{bg_filter}[bg_tinted]; "
        f"[1:a]showwaves=s=650x180:mode=line:colors={wave_color}:r=30:scale=sqrt[wave_raw]; "
        f"[wave_raw]split[wa][wb]; [wa][wb]overlay=x=1:y=1[wave]; "
        f"[2:v]scale=680:680[mock]; "
        f"[bg_tinted][3:v]overlay=x=0:y=0[bg_card_overlay]; "
        f"[bg_card_overlay][4:v]overlay=x={capsule_x}:y='{scroll_expr}':eval=frame[bg_highlighted]; "
        f"[bg_highlighted][mock]overlay=x=1160:y=140[bg_mock]; "
        f"[bg_mock][wave]overlay=x=1175:y=800[finalv]"
    )

    
    cmd = [
        "ffmpeg", "-y",
        *bg_input.split(),
        "-i", audio_path,
        "-i", mockup_path,
        "-i", overlay_path,
        "-i", capsule_path,
        "-filter_complex", filter_complex,
        "-map", "[finalv]",
        "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", "-threads", "2",
        "-c:a", "aac", "-b:a", "192000",
        "-t", str(total_duration),
        output_video_path
    ]
    
    try:
        print(f"Compiling 16:9 Showcase Video: {output_video_path}")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return os.path.exists(output_video_path)
    except Exception as e:
        print(f"Failed to compile 16:9 video: {e}")
        return False
    finally:
        if os.path.exists(capsule_path):
            try:
                os.remove(capsule_path)
            except Exception:
                pass
        if temp_bg_gradient and os.path.exists(temp_bg_gradient):
            try:
                os.remove(temp_bg_gradient)
            except Exception:
                pass

def ease_in_out(t: float) -> float:
    """Helper for smooth transitions."""
    if t < 0.5:
        return 2.0 * t * t
    return -1.0 + (4.0 - 2.0 * t) * t

def draw_marquee_text(draw, img, text, font, fill, y_pos, width, max_w, t_rel):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    if tw > max_w:
        scroll_dist = tw - max_w
        speed = 80.0  # pixels per second
        scroll_time = scroll_dist / speed
        loop_dur = 1.5 + scroll_time + 1.5  # 1.5s start pause, 1.5s end pause
        t_mod = t_rel % loop_dur
        if t_mod < 1.5:
            x_off = 0
        elif t_mod < 1.5 + scroll_time:
            x_off = int((t_mod - 1.5) / scroll_time * scroll_dist)
        else:
            x_off = scroll_dist
            
        canvas_h = th + 40
        with Image.new("RGBA", (tw + 40, canvas_h), (0, 0, 0, 0)) as txt_canvas:
            tc = ImageDraw.Draw(txt_canvas)
            tc.text((20 - bbox[0], 20 - bbox[1]), text, fill=fill, font=font)
            
            with txt_canvas.crop((20 + x_off, 0, 20 + x_off + max_w, canvas_h)) as visible:
                main_x = (width - max_w) // 2
                main_y = y_pos - 20 + bbox[1]
                img.paste(visible, (main_x, main_y), visible)
    else:
        draw.text((width // 2, y_pos), text, fill=fill, font=font, anchor="ms")

def render_scrolling_lyric_frame(
    width: int,
    height: int,
    t: float,
    markers: List[dict],
    genre: str,
    output_path: str,
    color_palette=None,
    font_family: str = "Nunito",
    accent_color_override=None
):
    """Renders a single frame for the Spotify-style vertical lyric scrolling Shorts video."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
    if accent_color_override:
        accent_color = accent_color_override
    elif color_palette:
        accent_color = color_palette[2]
    else:
        accent_color = gconfig["text_color"]
    
    font_large = get_font(font_family, 56, is_bold=True)
    font_small = get_font(font_family, 32, is_bold=True)
        
    active_idx = 0
    for idx, m in enumerate(markers):
        if m["start"] <= t <= m["end"]:
            active_idx = idx
            break
    else:
        active_idx = len(markers) - 1
        
    current_marker = markers[active_idx]
    
    scroll_offset = 0.0
    trans_start = current_marker["end"] - 0.5
    if t >= trans_start and active_idx < len(markers) - 1:
        progress = (t - trans_start) / 0.5
        scroll_offset = ease_in_out(min(1.0, max(0.0, progress)))
        
    cy = 1350
    gap = 80
    
    # Draw previous item
    if active_idx > 0 or scroll_offset > 0.0:
        prev_name = markers[active_idx - 1]["name"]
        if scroll_offset > 0.0:
            p_text = current_marker["name"]
            p_text_disp = p_text[:24] + "..." if len(p_text) > 24 else p_text
            y_pos = int(cy - gap * scroll_offset)
            font_size = int(56 - 24 * scroll_offset)
            opacity = int(255 - 135 * scroll_offset)
            color = tuple(int(255 - (255 - accent_color[i]) * (1.0 - scroll_offset)) for i in range(3))
        else:
            p_text = prev_name
            p_text_disp = p_text[:24] + "..." if len(p_text) > 24 else p_text
            y_pos = cy - gap
            font_size = 32
            opacity = 120
            color = accent_color
            
        try:
            f_prev = get_font(font_family, font_size, is_bold=True)
        except Exception:
            f_prev = font_small
            
        draw.text((width // 2, y_pos), p_text_disp, fill=(*color, opacity), font=f_prev, anchor="ms")
        
    # Draw active item
    if scroll_offset > 0.0:
        next_text = markers[active_idx + 1]["name"]
        next_text_disp = next_text[:24] + "..." if len(next_text) > 24 else next_text
        y_pos_next = int(cy + gap - gap * scroll_offset)
        font_size_next = int(32 + 24 * scroll_offset)
        opacity_next = int(120 + 135 * scroll_offset)
        color_next = tuple(int(255 - (255 - accent_color[i]) * scroll_offset) for i in range(3))
        
        try:
            f_next = get_font(font_family, font_size_next, is_bold=True)
        except Exception:
            f_next = font_large
        draw.text((width // 2, y_pos_next), next_text_disp, fill=(*color_next, opacity_next), font=f_next, anchor="ms")
    else:
        try:
            f_act = get_font(font_family, 56, is_bold=True)
        except Exception:
            f_act = font_large
            
        # Draw focused active text with marquee animation
        t_rel = t - current_marker["start"]
        draw_marquee_text(draw, img, current_marker["name"], f_act, (*accent_color, 255), cy, width, 880, t_rel)
        
        if active_idx < len(markers) - 1:
            next_name = markers[active_idx + 1]["name"]
            next_name_disp = next_name[:24] + "..." if len(next_name) > 24 else next_name
            draw.text((width // 2, cy + gap), next_name_disp, fill=(*accent_color, 120), font=font_small, anchor="ms")
            
    img.save(output_path, "PNG")
    img.close()

def compile_video_9_16_shorts(audio_path: str, mockup_path: str, output_video_path: str, genre: str, pack_name: str, markers: List[dict], color_palette=None, pexels_video_path: Optional[str] = None, style: Optional[str] = None) -> bool:
    """
    Compiles the 9:16 vertical YouTube Shorts video.
    Uses frame sequence lyric scrolling animation.
    """
    sconfig = MULTIPLE_STYLES[style] if (style and style in MULTIPLE_STYLES) else None
    
    if color_palette:
        color1, color2, text_color_rgb = color_palette
        wave_color = hex_to_ffmpeg_color(text_color_rgb)
    elif sconfig:
        color1, color2 = sconfig["bg_gradient"]
        text_color_rgb = sconfig["text_color"]
        wave_color = sconfig["wave_color"]
        color_palette = (color1, color2, text_color_rgb)
    else:
        gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
        color1, color2 = gconfig["bg_gradient"]
        text_color_rgb = gconfig["text_color"]
        wave_color = hex_to_ffmpeg_color(text_color_rgb)
        color_palette = (color1, color2, text_color_rgb)
        
    tint_color = hex_to_ffmpeg_color(color1)
    
    # Find background video (Try passed Pexels video first, then fetch Pexels, then local assets, then gradient fallback)
    pexels_video = pexels_video_path if pexels_video_path and os.path.exists(pexels_video_path) else get_pexels_background_video()
    temp_bg_gradient = None
    
    if pexels_video:
        bg_video_path = pexels_video
        bg_input = f"-stream_loop -1 -i {bg_video_path}"
        bg_filter = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,{generate_ffmpeg_tint_filter(tint_color, '1080x1920')}"
    else:
        bg_video = "bg_loop_1.mp4"
        if os.path.exists(ASSETS_DIR):
            loops = [f for f in os.listdir(ASSETS_DIR) if f.startswith("bg_loop") and f.endswith(".mp4")]
            if loops:
                bg_video = random.choice(loops)
        bg_video_path = os.path.join(ASSETS_DIR, bg_video)
        
        if not os.path.exists(bg_video_path):
            temp_bg_gradient = os.path.join(os.path.dirname(output_video_path), "temp_bg_gradient_shorts.png")
            gradient_img = generate_gradient(2000, 2000, color1, color2)
            gradient_img.save(temp_bg_gradient, "PNG")
            bg_input = f"-loop 1 -i {temp_bg_gradient}"
            bg_filter = "crop=w=1080:h=1920:x='(in_w-1080)/2 + (in_w-1080)/2*sin(t*0.1)':y='(in_h-1920)/2 + (in_h-1920)/2*cos(t*0.1)',setsar=1"
        else:
            bg_input = f"-stream_loop -1 -i {bg_video_path}"
            bg_filter = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,{generate_ffmpeg_tint_filter(tint_color, '1080x1920')}"
        
    duration = min(30.0, markers[-1]["end"])
    
    temp_frames_dir = os.path.join(os.path.dirname(output_video_path), "temp_shorts_frames")
    if os.path.exists(temp_frames_dir):
        try:
            shutil.rmtree(temp_frames_dir)
        except Exception:
            pass
    os.makedirs(temp_frames_dir, exist_ok=True)  # always recreate cleanly
    
    static_overlay_path = os.path.join(os.path.dirname(output_video_path), "temp_shorts_static.png")
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Resolve font from style or fall back to Nunito
    shorts_font_family = sconfig["font_family"] if sconfig else "Nunito"
    # Derive accent color from style config or color_palette override for frame renderer
    shorts_accent_color = text_color_rgb
    
    font_logo = get_font(shorts_font_family, 38, is_bold=True)
    font_title = get_font(shorts_font_family, 64, is_bold=True)
    font_sub = get_font(shorts_font_family, 26)
        
    draw.text((540, 240), "ARQIVE", fill=(255, 255, 255, 230), font=font_logo, anchor="ms")
    draw.text((540, 320), clean_title_for_shorts(pack_name), fill=text_color_rgb, font=font_title, anchor="ms")
    # Wave background card removed!
    draw.text((540, 1750), "🔗 FREE DOWNLOAD IN DESCRIPTION / PINNED MSG", fill=(245, 245, 250, 200), font=font_sub, anchor="ms")
    img.save(static_overlay_path, "PNG")
    
    print("Generating scrolling lyric frame sequences...")
    fps = 30
    total_frames = int(duration * fps) + 5
    for frame_idx in range(total_frames):
        t = frame_idx / fps
        frame_name = f"frame_{frame_idx:05d}.png"
        frame_path = os.path.join(temp_frames_dir, frame_name)
        render_scrolling_lyric_frame(
            1080, 1920, t, markers, genre, frame_path, color_palette,
            font_family=shorts_font_family,
            accent_color_override=shorts_accent_color
        )
        
    filter_complex = (
        f"[0:v]{bg_filter}[bg_tinted]; "
        f"[1:a]showwaves=s=880x160:mode=line:colors={wave_color}:r=30:scale=sqrt[wave_raw]; "
        f"[wave_raw]split[wa][wb]; [wa][wb]overlay=x=1:y=1[wave]; "
        f"[2:v]scale=750:750[mock]; "
        f"[bg_tinted][3:v]overlay=x=0:y=0[bg_overlay]; "
        f"[bg_overlay][mock]overlay=x=165:y=380[bg_mock]; "
        f"[bg_mock][wave]overlay=x=100:y=1520[bg_wave]; "
        f"[bg_wave][4:v]overlay=x=0:y=0[finalv]"
     )
    
    cmd = [
        "ffmpeg", "-y",
        *bg_input.split(),
        "-i", audio_path,
        "-i", mockup_path,
        "-i", static_overlay_path,
        "-framerate", str(fps),
        "-i", os.path.join(temp_frames_dir, "frame_%05d.png"),
        "-filter_complex", filter_complex,
        "-map", "[finalv]",
        "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", "-threads", "2",
        "-c:a", "aac", "-b:a", "192000",
        "-t", str(duration),
        output_video_path
    ]
    
    try:
        print(f"Compiling 9:16 Shorts Video: {output_video_path}")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return os.path.exists(output_video_path)
    except Exception as e:
        print(f"Failed to compile Shorts video: {e}")
        return False
    finally:
        if os.path.exists(static_overlay_path):
            try:
                os.remove(static_overlay_path)
            except Exception:
                pass
        if os.path.exists(temp_frames_dir):
            try:
                shutil.rmtree(temp_frames_dir)
            except Exception:
                pass
        if temp_bg_gradient and os.path.exists(temp_bg_gradient):
            try:
                os.remove(temp_bg_gradient)
            except Exception:
                pass

def clean_title_for_shorts(name: str) -> str:
    """Gets uppercase clean name for Shorts center graphic."""
    title = name.replace("Arqive", "").replace("[AQ]", "").replace("Pack", "").strip()
    title = re.sub(r"#\d+", "", title)
    return title.strip().upper()

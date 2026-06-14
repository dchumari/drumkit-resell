import os
import re
import random
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Dict
from config import GENRE_COLORS, ASSETS_DIR

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
            import subprocess
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", filepath]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            return float(data["format"]["duration"])
        except Exception:
            return 2.5

def compile_preview_audio(showcase_files: List[Tuple[str, str]], output_audio_path: str, voice_tag_path: str) -> Tuple[str, List[dict]]:
    """
    Trims, concatenates, and mixes voice tag watermarks into the showcase audio.
    Returns (output_audio_path, markers)
    """
    import config
    temp_concat = "temp_concat.wav"
    inputs = []
    filter_parts = []
    concat_parts = []
    current_time = 0.0
    markers = []
    
    # 1. Build trim and concat filter
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
                
        inputs.extend(["-i", fpath])
        filter_parts.append(f"[{idx}:a]apad,atrim=end={duration},asetpts=PTS-STARTPTS[a{idx}]")
        concat_parts.append(f"[a{idx}]")
        
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

    if not showcase_files:
        return output_audio_path, []

    filter_str = "; ".join(filter_parts) + "; " + "".join(concat_parts) + f"concat=n={len(showcase_files)}:v=0:a=1[aout]"
    cmd_concat = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_str, "-map", "[aout]", temp_concat]
    
    try:
        subprocess.run(cmd_concat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error concatenating showcase audio: {e}")
        if len(showcase_files) > 0:
            shutil.copy(showcase_files[0][0], output_audio_path)
        return output_audio_path, markers

    # 2. Mix in the voice tag watermarks
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
        if os.path.exists(temp_concat):
            os.remove(temp_concat)
            
    return output_audio_path, markers

def re_strip_meta(text: str) -> str:
    """Removes trailing bracket metadata."""
    import re
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
    """Generates an SRT subtitle file to show currently playing tracks."""
    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, m in enumerate(markers, 1):
            start = format_time_srt(m["start"])
            end = format_time_srt(m["end"])
            f.write(f"{idx}\n")
            f.write(f"{start} --> {end}\n")
            # Text layout: e.g., "Playing: 808 - Heavy" in cyan
            f.write(f"NOW PLAYING: {m['category'].upper()} - {m['name'].upper()}\n\n")

def create_tracklist_overlay(pack_name: str, genre: str, markers: List[dict], output_img_path: str):
    """Generates a transparent 1920x1080 PNG image with a tracklist on the left."""
    img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
    text_color = gconfig["text_color"]
    border_color = gconfig["border_color"]
    
    try:
        font_logo = ImageFont.truetype("arialbd.ttf", 36)
        font_sub = ImageFont.truetype("arial.ttf", 20)
        font_header = ImageFont.truetype("arialbd.ttf", 26)
        font_item = ImageFont.truetype("arial.ttf", 22)
    except IOError:
        font_logo = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_item = ImageFont.load_default()

    # Draw Brand Logo
    draw.text((80, 80), "ARQIVE ARCHIVE", fill=(255, 255, 255, 250), font=font_logo)
    draw.text((80, 125), f"PREMIUM {genre.upper()} SELECTION", fill=text_color, font=font_sub)
    draw.line([(80, 160), (500, 160)], fill=border_color, width=2)
    
    # Draw Left Tracklist
    draw.text((80, 185), "KIT SHOWCASE:", fill=text_color, font=font_header)
    
    # We display up to 15 items in the list to avoid vertical overflow
    y = 230
    listed_count = 0
    # Group markers by category for clean listing
    categories_seen = []
    
    for m in markers:
        if listed_count >= 14:
            draw.text((100, y), "...and more premium samples", fill=(180, 180, 180, 150), font=font_item)
            break
            
        if m["category"] not in categories_seen:
            categories_seen.append(m["category"])
            draw.text((90, y), f"[{m['category'].upper()}]", fill=border_color, font=font_sub)
            y += 30
            
        # Draw track item
        draw.text((110, y), f"• {m['name'][:28]}", fill=(240, 240, 245, 220), font=font_item)
        y += 32
        listed_count += 1

    # Draw a clean outline border on the left panel
    draw.rectangle([50, 50, 550, 1030], outline=(*border_color, 80), width=2)
    
    img.save(output_img_path, "PNG")
    print(f"Tracklist overlay image created: {output_img_path}")

def hex_to_ffmpeg_color(rgb: tuple) -> str:
    """Converts (R,G,B) tuple to FFmpeg color string like 0xRRGGBB."""
    return f"0x{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

def compile_video_16_9(audio_path: str, mockup_path: str, overlay_path: str, output_video_path: str, genre: str, markers: List[dict], srt_path: str) -> bool:
    """
    Compiles the 16:9 landscape YouTube showcase video.
    """
    gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
    rgb_tint = gconfig["bg_gradient"][0]
    tint_color = hex_to_ffmpeg_color(rgb_tint)
    wave_color = hex_to_ffmpeg_color(gconfig["text_color"])
    
    # Find random background video
    bg_video = "bg_loop_1.mp4"  # Default fallback
    if os.path.exists(ASSETS_DIR):
        loops = [f for f in os.listdir(ASSETS_DIR) if f.startswith("bg_loop") and f.endswith(".mp4")]
        if loops:
            bg_video = random.choice(loops)
    bg_video_path = os.path.join(ASSETS_DIR, bg_video)
    
    if not os.path.exists(bg_video_path):
        print(f"Background video loop {bg_video_path} not found. Visuals might fail.")
        # Create a black fallback video input using lavfi if no bg video exists
        bg_input = "-f lavfi -i color=c=black:s=1920x1080"
    else:
        bg_input = f"-stream_loop -1 -i {bg_video_path}"

    # Calculate total duration
    if not markers:
        print("Error: No markers provided for video compilation.")
        return False
    total_duration = markers[-1]["end"]
    
    # FFmpeg Filter Complex:
    # 1. Loop and scale background video to 1920x1080.
    # 2. Apply a transparent color tint blend (multiply) based on the genre.
    # 3. Create a reactive showwaves waveform visualizer from the audio.
    # 4. Overlay the tracklist PNG overlay.
    # 5. Overlay the 3D box mockup (scale to 600x600, place on right).
    # 6. Overlay the waveform under the 3D mockup.
    # 7. Burn in the SRT subtitle track showing the playing sample.
    
    filter_complex = (
        f"[0:v]scale=1920:1080,setsar=1[bg]; "
        f"color=c={tint_color}@0.4:s=1920x1080[tint]; "
        f"[bg][tint]blend=all_mode='multiply':all_opacity=0.6[bg_tinted]; "
        f"[1:a]showwaves=s=650x180:mode=line:colors={wave_color}:r=30[wave]; "
        f"[2:v]scale=600:600[mock]; "
        f"[bg_tinted][3:v]overlay=x=0:y=0[bg_overlay]; "
        f"[bg_overlay][mock]overlay=x=1200:y=180[bg_mock]; "
        f"[bg_mock][wave]overlay=x=1175:y=800[outv]"
    )
    
    # Subtitles must be burned using the subtitles filter. Note: FFmpeg requires absolute paths 
    # with double-backslashes or forward slashes for the subtitles filter on Windows.
    clean_srt_path = srt_path.replace("\\", "/").replace(":", "\\:")
    sub_filter = f"[outv]subtitles='{clean_srt_path}':force_style='Alignment=2,MarginV=60,FontSize=28,PrimaryColour=&H00FFFF&'[finalv]"
    filter_complex += f"; {sub_filter}"

    cmd = [
        "ffmpeg", "-y",
        *bg_input.split(),
        "-i", audio_path,
        "-i", mockup_path,
        "-i", overlay_path,
        "-filter_complex", filter_complex,
        "-map", "[finalv]",
        "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
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

def compile_video_9_16_shorts(audio_path: str, mockup_path: str, output_video_path: str, genre: str, pack_name: str) -> bool:
    """
    Compiles the 9:16 vertical YouTube Shorts video (15-45s max).
    Plays the first 1 or 2 loops.
    """
    gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
    tint_color = hex_to_ffmpeg_color(gconfig["bg_gradient"][0])
    wave_color = hex_to_ffmpeg_color(gconfig["text_color"])
    
    bg_video = "bg_loop_1.mp4"
    if os.path.exists(ASSETS_DIR):
        loops = [f for f in os.listdir(ASSETS_DIR) if f.startswith("bg_loop") and f.endswith(".mp4")]
        if loops:
            bg_video = random.choice(loops)
    bg_video_path = os.path.join(ASSETS_DIR, bg_video)
    
    if not os.path.exists(bg_video_path):
        bg_input = "-f lavfi -i color=c=black:s=1080x1920"
    else:
        bg_input = f"-stream_loop -1 -i {bg_video_path}"
        
    # Limit Shorts to 30 seconds
    duration = 30.0
    
    # Generate transparent Shorts Text Overlay
    overlay_path = "temp_shorts_overlay.png"
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font_logo = ImageFont.truetype("arialbd.ttf", 32)
        font_title = ImageFont.truetype("arialbd.ttf", 54)
        font_sub = ImageFont.truetype("arial.ttf", 26)
    except IOError:
        font_logo = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        
    draw.text((540, 250), "ARQIVE", fill=(255, 255, 255, 230), font=font_logo, anchor="ms")
    draw.text((540, 320), clean_title_for_shorts(pack_name), fill=gconfig["text_color"], font=font_title, anchor="ms")
    draw.text((540, 1600), "🔗 FREE DOWNLOAD IN DESCRIPTION / PINNED MSG", fill=(245, 245, 250, 200), font=font_sub, anchor="ms")
    img.save(overlay_path, "PNG")

    # Filter Complex:
    # 1. Scale background loop to 1080x1920 (fill).
    # 2. Tint background.
    # 3. Scale mockup to 750x750, place centered.
    # 4. Generate showwaves horizontal waveform visualizer, place below mockup.
    # 5. Overlay text image.
    filter_complex = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[bg]; "
        f"color=c={tint_color}@0.4:s=1080x1920[tint]; "
        f"[bg][tint]blend=all_mode='multiply':all_opacity=0.6[bg_tinted]; "
        f"[1:a]showwaves=s=880x200:mode=line:colors={wave_color}:r=30[wave]; "
        f"[2:v]scale=750:750[mock]; "
        f"[bg_tinted][3:v]overlay=x=0:y=0[bg_overlay]; "
        f"[bg_overlay][mock]overlay=x=165:y=500[bg_mock]; "
        f"[bg_mock][wave]overlay=x=100:y=1300[finalv]"
    )

    cmd = [
        "ffmpeg", "-y",
        *bg_input.split(),
        "-i", audio_path,
        "-i", mockup_path,
        "-i", overlay_path,
        "-filter_complex", filter_complex,
        "-map", "[finalv]",
        "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
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
        if os.path.exists(overlay_path):
            os.remove(overlay_path)

def clean_title_for_shorts(name: str) -> str:
    """Gets uppercase clean name for Shorts center graphic."""
    title = name.replace("Arqive", "").replace("[AQ]", "").replace("Pack", "").strip()
    title = re.sub(r"#\d+", "", title)
    return title.strip().upper()

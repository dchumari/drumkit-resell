import os
import sys
import shutil
import zipfile
import wave
import struct
import math
import random
import argparse

# Append the src/ folder to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
import cover_generator
import mockup_generator
import video_generator
import audio_processor

def generate_sine_wave(filepath: str, duration: float, freq: float):
    """Generates a simple mono sine wave WAV file using only the standard library wave module."""
    sample_rate = 44100
    num_samples = int(duration * sample_rate)
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with wave.open(filepath, 'w') as w:
        w.setnchannels(1)  # Mono
        w.setsampwidth(2)  # 16-bit
        w.setframerate(sample_rate)
        # Generate sine samples
        for i in range(num_samples):
            t = float(i) / sample_rate
            value = int(25000.0 * math.sin(2.0 * math.pi * freq * t))
            data = struct.pack('<h', value)
            w.writeframesraw(data)

def create_mock_zip(output_zip_path: str):
    """Creates a temporary mock ZIP folder containing audio samples of various categories."""
    temp_dir = "temp_mock_files"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Define files to create: (name, duration, frequency)
    mock_files = [
        ("Cymatics_808_Sub_C.wav", 5.0, 60.0),
        ("Wavgrind_Kick_Punchy.wav", 1.5, 90.0),
        ("Decap_Snare_Classic.wav", 1.5, 180.0),
        ("Splice_Hat_Closed.wav", 1.0, 800.0),
        ("Lofi_Melody_Loop_140BPM_Am.wav", 12.0, 440.0),
        ("SFX_Sweep_Down.wav", 3.0, 300.0),
        ("Perc_Rim_Shot.wav", 1.2, 500.0)
    ]
    
    for filename, dur, freq in mock_files:
        generate_sine_wave(os.path.join(temp_dir, filename), dur, freq)
        
    # Zip the mock files
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for f in os.listdir(temp_dir):
            zip_ref.write(os.path.join(temp_dir, f), f)
            
    # Cleanup directory
    shutil.rmtree(temp_dir)
    print(f"[OK] Generated mock source ZIP file at: {output_zip_path}")

def main():
    parser = argparse.ArgumentParser(description="Test local drumkit reselling pipeline without uploading.")
    parser.add_argument("--zip", type=str, help="Path to a real local .zip drumkit to process. (If omitted, a mock zip is generated)")
    parser.add_argument("--name", type=str, default="Apex", help="Rebranded name to use (default: Apex)")
    parser.add_argument("--genre", type=str, default="Trap", choices=["Trap", "RnB", "Lofi", "Phonk", "Hip-Hop", "Reggaeton", "House"], help="Genre category (default: Trap)")
    args = parser.parse_args()

    # Define output folder
    output_dir = os.path.join(config.BASE_DIR, "test_output")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Setup target zip
    target_zip = args.zip
    if not target_zip:
        target_zip = os.path.join(output_dir, "mock_source_pack.zip")
        create_mock_zip(target_zip)
        
    if not os.path.exists(target_zip):
        print(f"[ERROR] Source ZIP file does not exist: {target_zip}")
        return

    # Define local test paths
    temp_extract = os.path.join(output_dir, "temp_extract")
    cover_path = os.path.join(output_dir, "rebranded_cover.png")
    mockup_path = os.path.join(output_dir, "rebranded_mockup.png")
    overlay_path = os.path.join(output_dir, "tracklist_overlay.png")
    audio_path = os.path.join(output_dir, "preview_showcase.mp3")
    srt_path = os.path.join(output_dir, "subtitles.srt")
    video_path = os.path.join(output_dir, "showcase_video_16_9.mp4")
    shorts_path = os.path.join(output_dir, "showcase_shorts_9_16.mp4")
    rebranded_zip_base = os.path.join(output_dir, f"Arqive_{args.name}")
    
    # Clean up old output files
    for p in [temp_extract, cover_path, mockup_path, overlay_path, audio_path, srt_path, video_path, shorts_path]:
        if os.path.exists(p):
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)

    rebranded_full_name = f"Arqive {args.name}"
    print(f"\n=== Running Local Pipeline Test ===")
    print(f"Name:  {rebranded_full_name}")
    print(f"Genre: {args.genre}\n")

    try:
        # Step 1: Unzip Pack
        print("Step 1: Extracting source ZIP...")
        audio_processor.unzip_pack(target_zip, temp_extract)
        
        # Step 2: Brand whitewashing & categorization
        print("Step 2: Scanning & rebranding files (whitewashing metadata)...")
        cats, all_files = audio_processor.process_and_rename_kit(temp_extract)
        print(f"Found {len(all_files)} audio samples. Categorized:")
        for cat, files in cats.items():
            if files:
                print(f"  - {cat}: {len(files)} files")

        # Step 3: Generate cover and 3D mockup graphics
        print("\nStep 3: Rendering cover art & 3D mockup box...")
        cover_generator.generate_cover_art(rebranded_full_name, args.genre, cover_path)
        mockup_generator.generate_3d_mockup(cover_path, mockup_path, rebranded_full_name, args.genre)
        
        # Step 4: Create Audio Showcase
        print("\nStep 4: Compiling preview showcase audio mix...")
        showcase = audio_processor.select_preview_showcase(cats)
        voice_tag = os.path.join(config.ASSETS_DIR, "voice_tag.wav")
        # Ensure we check if voice_tag exists
        if not os.path.exists(voice_tag):
            print("  Note: voice_tag.wav not found in assets/. Compiling preview without watermarks.")
            voice_tag = ""
            
        video_generator.compile_preview_audio(showcase, audio_path, voice_tag)
        
        # Step 5: Generate video overlays and SRT subtitles
        print("\nStep 5: Creating visual overlay graphic and subtitles.srt...")
        
        # Build SRT marker timings and dict markers first
        markers = []
        current_time = 0.0
        for fpath, cat in showcase:
            duration = 12.0 if cat in ["Loops", "808s"] else 2.5
            fname = os.path.basename(fpath).replace("[AQ] ", "")
            for suffix in [".wav", ".mp3", ".aif", ".aiff"]:
                fname = fname.replace(suffix, "")
            markers.append({
                "name": video_generator.re_strip_meta(fname),
                "category": cat,
                "start": current_time,
                "end": current_time + duration
            })
            current_time += duration
        video_generator.create_srt_file(markers, srt_path)
        
        # Now create overlay image using markers dict list
        video_generator.create_tracklist_overlay(rebranded_full_name, args.genre, markers, overlay_path)
        
        # Step 6: Compile video files (using FFmpeg)
        # Temporarily append Gyan.FFmpeg to system path if needed to ensure subprocess runs
        # (This is a failsafe to ensure path environment gets loaded in current process)
        gyan_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links")
        if os.path.exists(gyan_path) and gyan_path not in os.environ["PATH"]:
            os.environ["PATH"] += ";" + gyan_path
            
        print("\nStep 6: Running FFmpeg to compile landscape 16:9 showreel...")
        v16_9_ok = video_generator.compile_video_16_9(audio_path, mockup_path, overlay_path, video_path, args.genre, markers, srt_path)
        
        print("Step 7: Running FFmpeg to compile vertical 9:16 Shorts showreel...")
        v9_16_ok = video_generator.compile_video_9_16_shorts(audio_path, mockup_path, shorts_path, args.genre, rebranded_full_name)
        
        # Step 8: Package Rebranded Zip
        print("\nStep 8: Packaging clean rebranded drumkit volume...")
        zip_files = audio_processor.zip_pack(temp_extract, rebranded_zip_base)
        
        # Cleanup temp extraction folder
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
            
        print("\n=================== PIPELINE TEST COMPLETED ===================")
        print("[SUCCESS] All generation, rendering, and processing tests completed.")
        print(f"Saved Rebranded Cover:   [cover](file:///{cover_path.replace('\\', '/')})")
        print(f"Saved 3D Mockup Box:    [mockup](file:///{mockup_path.replace('\\', '/')})")
        print(f"Saved Video Overlay:     [overlay](file:///{overlay_path.replace('\\', '/')})")
        print(f"Saved Showcase Audio:    [audio](file:///{audio_path.replace('\\', '/')})")
        print(f"Saved SRT Subtitles:     [subtitles](file:///{srt_path.replace('\\', '/')})")
        print(f"Saved Landscape Video:   [video_16_9](file:///{video_path.replace('\\', '/')})")
        print(f"Saved Vertical Shorts:   [video_9_16](file:///{shorts_path.replace('\\', '/')})")
        print("Saved Rebranded Zips:")
        for zf in zip_files:
            print(f"  - [zip](file:///{zf.replace('\\', '/')})")
        print("===============================================================")
        
    except Exception as e:
        print(f"\n[FAIL] Local Pipeline Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

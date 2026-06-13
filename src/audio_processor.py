import os
import re
import zipfile
import subprocess
import shutil
from typing import Dict, List, Tuple

# Common producer/brand keywords to strip
BRAND_KEYWORDS = [
    "cymatics", "wavgrind", "decap", "slate", "kyle beats", "looperman", 
    "splice", "producergrind", "kit", "drumkit", "samplepack", "pack",
    "exclusive", "premium", "drum"
]

AUDIO_EXTENSIONS = (".wav", ".mp3", ".aif", ".aiff", ".flac")

def unzip_pack(zip_path: str, extract_to: str):
    """Unzips the drumkit archive to the target folder."""
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"Extracted {zip_path} to {extract_to}")

def clean_text(text: str) -> str:
    """Removes branding words, BPM/Key annotations, and cleans up spacing/dashes."""
    cleaned = text
    
    # Remove BPM patterns like (140BPM), [140 BPM], 140BPM, 140 bpm case-insensitively
    cleaned = re.sub(r"(?i)[\(\[\]\)]?\s*\b\d{2,3}\s*bpm\b\s*[\(\[\]\)]?", "", cleaned)
    
    # Remove Key patterns like (Cmin), [A#], Cmin, F#maj, G#min, Am, F#
    cleaned = re.sub(r"(?i)[\(\[\]\)]?\s*\b[A-G][#b]?(?:min|maj|minor|major|m)?(?![a-zA-Z0-9#])\s*[\(\[\]\)]?", "", cleaned)
    
    for kw in BRAND_KEYWORDS:
        # Match case-insensitively with boundaries
        cleaned = re.sub(rf"(?i)\b{re.escape(kw)}\b", "", cleaned)
    
    # Clean up double spaces, leading/trailing spaces, and empty brackets
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\(\s*\)|\[\s*\]", "", cleaned)
    cleaned = cleaned.replace(" - - ", " - ").replace(" -- ", " - ")
    cleaned = cleaned.strip(" -_[]() ")
    return cleaned if cleaned else "Sample"

def parse_bpm_key(filename: str) -> Tuple[str, str]:
    """Attempts to extract BPM and Key from the filename."""
    bpm_match = re.search(r"\b(\d{2,3})\s*(?:bpm|BPM|Bpm)\b", filename)
    bpm = bpm_match.group(1) if bpm_match else ""
    
    # Match standard keys: e.g., Cmin, A#, F#maj, G#min, Am
    # Matches letters A-G followed by optional # or b, then followed by minor/major/min/maj/m/minor
    key_match = re.search(r"\b([A-G][#b]?(?:min|maj|minor|major|m)?)(?![a-zA-Z0-9#])", filename)
    key = key_match.group(1) if key_match else ""
    
    return bpm, key

def categorize_sample(filename: str, parent_folder: str) -> str:
    """Categorizes the sample based on filename and folder names."""
    path_text = f"{parent_folder}/{filename}".lower()
    
    if "808" in path_text or "sub" in path_text:
        return "808s"
    elif "kick" in path_text:
        return "Kicks"
    elif "snare" in path_text or "clap" in path_text or "rim" in path_text:
        return "Snares"
    elif "hat" in path_text or "openhat" in path_text or "shaker" in path_text or "crash" in path_text or "cymbal" in path_text:
        return "Hats"
    elif "loop" in path_text or "melody" in path_text or "synth" in path_text or "chord" in path_text or "stem" in path_text or "drum loop" in path_text:
        return "Loops"
    elif "perc" in path_text or "conga" in path_text or "bongo" in path_text or "cowbell" in path_text or "tom" in path_text:
        return "Percs"
    elif "fx" in path_text or "sound effect" in path_text or "riser" in path_text or "sweep" in path_text or "ambient" in path_text:
        return "FX"
    
    return "Others"

def process_and_rename_kit(root_dir: str) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Recursively renames files and folders, prefixes files with [AQ],
    categorizes audio samples, and returns the categories dictionary.
    """
    # 1. Rename files first (to keep directory structure intact during walk)
    all_renamed_files = []
    categories: Dict[str, List[str]] = {
        "808s": [], "Kicks": [], "Snares": [], "Hats": [], "Loops": [], "Percs": [], "FX": [], "Others": []
    }
    
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        for name in filenames:
            file_ext = os.path.splitext(name)[1].lower()
            if file_ext in AUDIO_EXTENSIONS:
                bpm, key = parse_bpm_key(name)
                # Strip file extension for cleaning
                base_name = os.path.splitext(name)[0]
                cleaned_name = clean_text(base_name)
                
                # Format: [AQ] CleanedName (140BPM) (Cmin).wav
                new_name = f"[AQ] {cleaned_name}"
                meta = []
                if bpm:
                    meta.append(f"{bpm}BPM")
                if key:
                    meta.append(key)
                if meta:
                    new_name += " " + " ".join(f"({m})" for m in meta)
                new_name += file_ext
                
                old_path = os.path.join(dirpath, name)
                new_path = os.path.join(dirpath, new_name)
                
                try:
                    os.rename(old_path, new_path)
                    folder_name = os.path.basename(dirpath)
                    cat = categorize_sample(new_name, folder_name)
                    categories[cat].append(new_path)
                    all_renamed_files.append(new_path)
                except Exception as e:
                    print(f"Error renaming file {old_path}: {e}")
                    categories["Others"].append(old_path)
            else:
                # For non-audio files (like text, images, PDF), clean branding or delete
                if name.lower().endswith((".txt", ".png", ".jpg", ".pdf")):
                    cleaned_name = clean_text(os.path.splitext(name)[0]) + os.path.splitext(name)[1]
                    old_path = os.path.join(dirpath, name)
                    new_path = os.path.join(dirpath, cleaned_name)
                    try:
                        os.rename(old_path, new_path)
                    except Exception:
                        pass

    # 2. Rename directories (bottom-up to avoid path breakages)
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        for name in dirnames:
            old_dir_path = os.path.join(dirpath, name)
            cleaned_dir_name = clean_text(name)
            new_dir_path = os.path.join(dirpath, cleaned_dir_name)
            if old_dir_path != new_dir_path:
                try:
                    os.rename(old_dir_path, new_dir_path)
                except Exception as e:
                    print(f"Error renaming directory {old_dir_path}: {e}")

    # Re-map categories to updated renamed paths (since parent directories changed)
    # We walk again to gather finalized absolute paths
    final_categories: Dict[str, List[str]] = {k: [] for k in categories.keys()}
    final_all_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for name in filenames:
            file_ext = os.path.splitext(name)[1].lower()
            if file_ext in AUDIO_EXTENSIONS:
                fpath = os.path.join(dirpath, name)
                folder_name = os.path.basename(dirpath)
                cat = categorize_sample(name, folder_name)
                final_categories[cat].append(fpath)
                final_all_files.append(fpath)
                
    return final_categories, final_all_files

def select_preview_showcase(categories: Dict[str, List[str]], max_per_cat: int = 5) -> List[Tuple[str, str]]:
    """
    Selects up to max_per_cat samples from each category to form a preview.
    Returns list of tuples: (file_path, category_name)
    """
    showcase = []
    # Order of showcase playback: Loops first, then 808s, Kicks, Snares, Hats, Percs, FX
    order = ["Loops", "808s", "Kicks", "Snares", "Hats", "Percs", "FX", "Others"]
    for cat in order:
        files = categories.get(cat, [])
        selected = files[:max_per_cat]  # Pick the first few
        for f in selected:
            showcase.append((f, cat))
    return showcase

def zip_pack(source_dir: str, output_zip_base: str) -> List[str]:
    """
    Zips the directory. If size exceeds 2GB (approx 1.9GB limit), 
    uses 7z to split it into 1.9GB volumes.
    Returns list of generated file paths.
    """
    # Calculate folder size
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(source_dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
            
    limit = 1.9 * 1024 * 1024 * 1024  # 1.9GB limit
    
    if total_size > limit:
        print(f"Folder size ({total_size / 1024 / 1024 / 1024:.2f}GB) exceeds 1.9GB. Splitting using 7z.")
        # Output base name like rebranded_kit.zip
        output_zip = output_zip_base + ".zip"
        if os.path.exists(output_zip):
            os.remove(output_zip)
            
        # Command: 7z a -v1900m <output_zip> <source_dir>/*
        cmd = ["7z", "a", "-v1900m", output_zip, os.path.join(source_dir, "*")]
        try:
            subprocess.run(cmd, check=True)
            # Find generated split files: output.zip.001, output.zip.002, etc.
            # 7z split outputs are located in the parent directory of output_zip
            parent_dir = os.path.dirname(os.path.abspath(output_zip))
            base_name = os.path.basename(output_zip)
            split_files = []
            for f in os.listdir(parent_dir):
                if f.startswith(base_name) and (f.endswith(".zip") or re.search(r"\.\d{3}$", f)):
                    split_files.append(os.path.join(parent_dir, f))
            # Sort files alphabetically (so .zip.001 is before .zip.002)
            split_files.sort()
            return split_files
        except Exception as e:
            print(f"7z splitting failed: {e}. Falling back to standard zip.")
            
    # Standard single ZIP file creation
    output_zip = output_zip_base + ".zip"
    if os.path.exists(output_zip):
        os.remove(output_zip)
        
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for dirpath, dirnames, filenames in os.walk(source_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                arcname = os.path.relpath(filepath, source_dir)
                zip_ref.write(filepath, arcname)
                
    print(f"Standard ZIP created: {output_zip}")
    return [output_zip]

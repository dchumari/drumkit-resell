import os
import re
import zipfile
import subprocess
import shutil
from typing import Dict, List, Tuple, Optional

# Common producer/brand keywords to strip
BRAND_KEYWORDS = [
    "cymatics", "wavgrind", "decap", "slate", "kyle beats", "looperman", 
    "splice", "producergrind", "kit", "drumkit", "samplepack", "pack",
    "exclusive", "premium", "drum"
]

AUDIO_EXTENSIONS = (".wav", ".mp3", ".aif", ".aiff", ".flac")
ALLOWED_EXTENSIONS = (".wav", ".mp3", ".aif", ".aiff", ".flac", ".fxp", ".fxb", ".fst", ".nki", ".sfz", ".nkm", ".h2b", ".mid", ".midi", ".flp")

def extract_nested_zips(directory: str):
    """Recursively scans for and extracts any nested .zip, .rar, or .7z files in the directory."""
    import zipfile
    found_any = True
    while found_any:
        found_any = False
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in (".zip", ".rar", ".7z"):
                    archive_path = os.path.join(dirpath, filename)
                    base_name = os.path.splitext(filename)[0]
                    extract_dir = os.path.join(dirpath, base_name)
                    os.makedirs(extract_dir, exist_ok=True)
                    
                    print(f"Extracting nested archive: {archive_path} -> {extract_dir}")
                    extracted = False
                    if ext == ".zip":
                        try:
                            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                                zip_ref.extractall(extract_dir)
                            extracted = True
                        except Exception as err:
                            print(f"Failed to extract nested zip {archive_path} with zipfile: {err}. Trying 7z...")
                    
                    if not extracted:
                        cmd = ["7z", "x", archive_path, f"-o{extract_dir}", "-y"]
                        try:
                            subprocess.run(cmd, check=True, capture_output=True, text=True)
                            extracted = True
                        except Exception as e7z:
                            print(f"7z fallback extraction failed for {archive_path}: {e7z}")
                    
                    # Delete the nested archive file
                    try:
                        os.remove(archive_path)
                    except Exception as e:
                        print(f"Failed to remove nested archive {archive_path}: {e}")
                        
                    found_any = True
                    break # break inner loop to restart walking since files changed
            if found_any:
                break

def unzip_pack(zip_path: str, extract_to: str):
    """Unzips the drumkit archive or copies directory contents to the target folder."""
    os.makedirs(extract_to, exist_ok=True)
    if os.path.isdir(zip_path):
        print(f"Path {zip_path} is a directory. Moving contents to {extract_to}")
        for item in os.listdir(zip_path):
            s = os.path.join(zip_path, item)
            d = os.path.join(extract_to, item)
            shutil.move(s, d)
    else:
        # Try standard zipfile first
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            print(f"Extracted {zip_path} to {extract_to} using standard zipfile.")
        except Exception as zip_err:
            print(f"Standard zipfile extraction failed: {zip_err}. Trying 7z fallback...")
            cmd = ["7z", "x", zip_path, f"-o{extract_to}", "-y"]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                print(f"Extracted {zip_path} to {extract_to} using 7z.")
            except Exception as e7z:
                print(f"7z extraction failed: {e7z}")
                raise zip_err

    # Recursively extract any nested zip files
    extract_nested_zips(extract_to)

def clean_text(text: str) -> str:
    """Removes branding words, BPM/Key annotations, usernames/domains, and cleans up spacing/dashes."""
    cleaned = text
    
    # 1. Remove URLs and domain names (e.g. http://... or slapdat.xyz)
    cleaned = re.sub(r"https?://[^\s()<>\"]+", "", cleaned)
    cleaned = re.sub(r"(?i)\b[a-zA-Z0-9-]+\.(?:com|xyz|net|org|co|uk|de|fm|io|edu|gov)\b", "", cleaned)
    
    # 2. Remove hex hashes (MD5 or SHA-256) and optional surrounding underscores
    cleaned = re.sub(r"(?i)_?[a-fA-F0-9]{32,64}_?", "", cleaned)
    
    # 3. Remove usernames starting with @ (e.g. @slapdat.xyz or @clpz)
    cleaned = re.sub(r"@[a-zA-Z0-9_.-]+", "", cleaned)
    
    # 4. Convert special characters to spaces (e.g., !, _, +, =, -, |, ~, etc.)
    # Running this before BPM/Key ensures word boundaries match correctly on spaces
    cleaned = re.sub(r"[!_+=\-\|~`@#$%^&*:;\"'<>,?/]", " ", cleaned)
    
    # 5. Remove BPM patterns like (140BPM), [140 BPM], 140BPM, 140 bpm case-insensitively
    cleaned = re.sub(r"(?i)[\(\[\]\)]?\s*\b\d{2,3}\s*bpm\b\s*[\(\[\]\)]?", "", cleaned)
    
    # 6. Remove Key patterns like (Cmin), [A#], Cmin, F#maj, G#min, Am, F# (supporting optional spaces before quality)
    cleaned = re.sub(r"(?i)[\(\[\]\)]?\s*\b[A-G][#b]?(?:\s*(?:min|maj|minor|major|m))?(?![a-zA-Z0-9#])\s*[\(\[\]\)]?", "", cleaned)
    
    # 6.5 Convert any remaining brackets/parentheses to spaces
    cleaned = re.sub(r"[\(\)\[\]{}]", " ", cleaned)
    
    # 7. Remove predefined brand keywords
    for kw in BRAND_KEYWORDS:
        cleaned = re.sub(rf"(?i)\b{re.escape(kw)}\b", "", cleaned)
        
    # 8. Clean up double spaces, leading/trailing spaces, and empty brackets
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\(\s*\)|\[\s*\]|\{\s*\}", "", cleaned)
    cleaned = cleaned.strip(" -_[](){} ")
    
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

CATEGORY_KEYWORDS = {
    "808": "808S",
    "sub": "808S",
    "kick": "KICKS",
    "snare": "SNARES",
    "clap": "CLAPS",
    "hat": "HATS",
    "hihat": "HATS",
    "openhat": "HATS",
    "oh": "HATS",
    "hh": "HATS",
    "crash": "HATS",
    "cymbal": "HATS",
    "shaker": "HATS",
    "loop": "LOOPS",
    "melody": "LOOPS",
    "melodies": "LOOPS",
    "synth": "LOOPS",
    "chord": "LOOPS",
    "stem": "LOOPS",
    "guitar": "LOOPS",
    "piano": "LOOPS",
    "keys": "LOOPS",
    "flute": "LOOPS",
    "bell": "LOOPS",
    "string": "LOOPS",
    "brass": "LOOPS",
    "perc": "PERCS",
    "conga": "PERCS",
    "bongo": "PERCS",
    "cowbell": "PERCS",
    "tom": "PERCS",
    "rim": "PERCS",
    "fx": "FX",
    "effect": "FX",
    "riser": "FX",
    "sweep": "FX",
    "ambient": "FX",
    "chant": "VOX",
    "vox": "VOX",
    "vocal": "VOX",
    "midi": "MIDI"
}

def pluralize_word(word: str) -> str:
    """Pluralizes a single word in uppercase."""
    word_upper = word.upper().strip()
    if not word_upper:
        return ""
    if word_upper.endswith("S"):
        return word_upper
    if word_upper.endswith("Y"):
        if word_upper.endswith(("AY", "EY", "OY", "UY")):
            return word_upper + "S"
        return word_upper[:-1] + "IES"
    if word_upper.endswith(("SH", "CH", "X", "Z", "SS")):
        return word_upper + "ES"
    return word_upper + "S"

def pluralize_category(cat: str) -> str:
    """Pluralizes a potentially multi-word category in uppercase."""
    cat_upper = cat.upper().strip()
    words = cat_upper.split()
    if not words:
        return "OTHERS"
    # Pluralize only the last word if it's not already plural
    last_word = words[-1]
    words[-1] = pluralize_word(last_word)
    return " ".join(words)

def parse_category_and_descriptor(rel_path: str) -> Tuple[str, str]:
    """
    Parses the relative path to extract the main category (in CAPS) and a descriptor.
    If no standard keywords are found, it uses the cleaned, capitalized, and pluralized
    leaf folder name as a custom category.
    """
    # Replace backslashes with forward slashes and split
    parts = rel_path.replace("\\", "/").strip("/").split("/")
    
    # Strip any allowed extensions from parts first to avoid them leaking into category/descriptor
    for i in range(len(parts)):
        part_lower = parts[i].lower()
        for ext in ALLOWED_EXTENSIONS:
            if part_lower.endswith(ext):
                parts[i] = parts[i][:-len(ext)]
                break
                
    # Clean each part to wash branding/special chars
    cleaned_parts = [clean_text(p) for p in parts if p.strip()]
    if not cleaned_parts:
        return "OTHERS", ""
        
    # Search from right to left for a category match
    cat_part_idx = -1
    matched_cat = ""
    matched_kw = ""
    
    for idx in range(len(cleaned_parts) - 1, -1, -1):
        part_lower = cleaned_parts[idx].lower()
        for kw, target_cat in CATEGORY_KEYWORDS.items():
            if kw in part_lower:
                matched_cat = target_cat
                cat_part_idx = idx
                matched_kw = kw
                break
        if matched_cat:
            break
            
    if matched_cat:
        # Standard category found
        if matched_cat == "LOOPS":
            cat_folder_name = cleaned_parts[cat_part_idx]
            cat_folder_lower = cat_folder_name.lower()
            
            # Case A: Generic Loops folder with a child folder (e.g. Loops/Melody)
            if (cat_folder_lower == "loops" or cat_folder_lower == "loop") and len(cleaned_parts) > cat_part_idx + 1:
                spec_folder = cleaned_parts[cat_part_idx + 1]
                spec_lower = spec_folder.lower()
                if "loop" not in spec_lower:
                    matched_cat = singularize_category(spec_folder).upper() + " LOOPS"
                else:
                    matched_cat = pluralize_category(spec_folder)
                
                descriptor_parts = []
                for idx in range(cat_part_idx + 2, len(cleaned_parts)):
                    descriptor_parts.append(cleaned_parts[idx].lower())
                descriptor = " ".join(descriptor_parts).strip()
                return matched_cat, descriptor
                
            # Case B: Specific Loops folder (e.g. Melody Loops/Dry)
            else:
                LOOP_INSTRUMENTS = {"guitar", "piano", "synth", "chord", "melody", "melodies", "stem", "flute", "bell", "string", "brass", "keys"}
                
                cleaned_folder_desc = cat_folder_lower
                # Strip loop keywords
                cleaned_folder_desc = re.sub(r"(?i)\bloops?\b", "", cleaned_folder_desc)
                # Strip matched keyword
                if matched_kw:
                    cleaned_folder_desc = re.sub(rf"(?i)\b{re.escape(matched_kw)}s?\b", "", cleaned_folder_desc)
                cleaned_folder_desc = re.sub(r"\s+", " ", cleaned_folder_desc).strip()
                
                if matched_kw in LOOP_INSTRUMENTS:
                    inst_name = singularize_category(matched_kw).upper()
                    if cleaned_folder_desc:
                        matched_cat = f"{cleaned_folder_desc.upper()} {inst_name} LOOPS"
                    else:
                        matched_cat = f"{inst_name} LOOPS"
                else:
                    if cleaned_folder_desc:
                        matched_cat = cleaned_folder_desc.upper() + " LOOPS"
                    else:
                        # If empty, fallback to orig_clean (or LOOPS if empty)
                        orig_clean = cat_folder_lower.replace("loops", "").replace("loop", "").strip()
                        if orig_clean:
                            matched_cat = orig_clean.upper() + " LOOPS"
                        else:
                            matched_cat = "LOOPS"
                    
                descriptor_parts = []
                for idx in range(cat_part_idx + 1, len(cleaned_parts)):
                    descriptor_parts.append(cleaned_parts[idx].lower())
                descriptor = " ".join(descriptor_parts).strip()
                return matched_cat, descriptor
                
        # Build descriptor for other standard categories
        descriptor_parts = []
        for idx in range(cat_part_idx + 1, len(cleaned_parts)):
            descriptor_parts.append(cleaned_parts[idx].lower())
            
        cat_folder_name = cleaned_parts[cat_part_idx]
        part_lower = cat_folder_name.lower()
        cleaned_folder_desc = part_lower
        for kw in CATEGORY_KEYWORDS.keys():
            if kw in cleaned_folder_desc:
                cleaned_folder_desc = re.sub(rf"(?i)\b{re.escape(kw)}s?\b", "", cleaned_folder_desc)
                
        cleaned_folder_desc = re.sub(r"\s+", " ", cleaned_folder_desc).strip()
        if cleaned_folder_desc:
            descriptor_parts.insert(0, cleaned_folder_desc)
            
        descriptor = " ".join(descriptor_parts)
        descriptor = re.sub(r"\s+", " ", descriptor).strip()
        return matched_cat, descriptor
    else:
        # No standard category found: Use cleaned, capitalized, and pluralized leaf folder name!
        leaf_folder = cleaned_parts[-1]
        custom_cat = pluralize_category(leaf_folder)
        
        # If there are parent directories above the leaf, use the immediate parent as descriptor
        descriptor = ""
        if len(cleaned_parts) > 1:
            descriptor = cleaned_parts[-2].lower()
            
        return custom_cat, descriptor

def query_ai_sample_names(category: str, count: int, genre: str) -> List[str]:
    """Queries OpenRouter to generate unique, premium, genre-styled names for a sample category."""
    import json
    import urllib.request
    import urllib.parse
    import config
    
    if not getattr(config, "OPENROUTER_API_KEY", ""):
        print("OpenRouter API key is missing. Using local fallback pool.")
        return []
        
    url = f"{config.OPENROUTER_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/arqive-developer/drumkit-reseller",
    }
    
    # Custom style prompt based on genre
    genre_lower = genre.lower()
    if "trap" in genre_lower or "phonk" in genre_lower:
        style_desc = "dark, aggressive, heavy, distorted, gritty, unhinged, underground, street, industrial"
    elif "lofi" in genre_lower or "rnb" in genre_lower or "chill" in genre_lower or "soul" in genre_lower:
        style_desc = "smooth, warm, dusty, vinyl, vintage, cozy, velvet, atmospheric, retro, dream, sunset, night"
    else:
        style_desc = "premium, clean, modern, sharp, digital, futuristic, space, solid, club, electronic"
        
    prompt = (
        f"Generate a list of exactly {count} unique, creative, short (one-word), premium-sounding name descriptors "
        f"suitable for naming {category} samples in a drum kit.\n"
        f"Genre style: {genre.upper()} ({style_desc}).\n"
        f"Instructions:\n"
        f"1. Generate names like 'Cave', 'Room', 'Swamp', 'Slime', 'Explode', 'Trauma', 'Haze', 'Static', 'Sizzle'.\n"
        f"2. Names must be single-word adjectives or nouns. Do not include numbers.\n"
        f"3. Return the response in strict JSON format containing a single list of strings like: [\"Name1\", \"Name2\", ...]"
    )
    
    payload = {
        "model": getattr(config, "OPENROUTER_MODEL", "deepseek/deepseek-v4-flash"),
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"].strip()
            # Clean possible markdown json wrapper: ```json ... ```
            content_cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.MULTILINE).strip()
            parsed = json.loads(content_cleaned)
            if isinstance(parsed, list):
                return [str(w).strip().title() for w in parsed if w]
    except Exception as e:
        print(f"DeepSeek AI sample naming query failed: {e}. Using local fallback.")
    return []

FALLBACK_NAMES = {
    "808S": {
        "dark": ["Swamp", "Trauma", "Viscera", "Gutshriek", "Explode", "Meatgrinder", "Slime", "Bonegrind", "God", "Voodoo", "Hades", "Pluto", "Titan", "Beast", "Thump", "Rumble", "Tremor", "Quake", "Grave", "Toxic", "Sludge", "Reaper", "Abyss", "Phantom", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Doom"],
        "smooth": ["Warmth", "Velvet", "Haze", "Dream", "Clouds", "Swell", "Submerge", "Sunset", "Vibe", "Cozy", "Chill", "Dusk", "Dawn", "Aura", "Static", "Vinyl", "Sable", "Silk", "Lush", "Soft", "Glow", "Breeze", "Float", "Serene", "Mist", "Fade", "Shimmer", "Amber", "Pulse", "Eon"],
        "clean": ["Solid", "Concrete", "Steel", "Anvil", "Piston", "Strike", "Knock", "Impact", "Apex", "Vortex", "Static", "Nova", "Pulse", "Punch", "Click", "Drive", "Stomp", "Hammer", "Force", "Limit", "Axis", "Core", "Cyber", "Grid", "Matrix", "Tech", "Volt", "Wave", "Sonic", "Sync"]
    },
    "KICKS": {
        "dark": ["Punch", "Heavy", "Hard", "Solid", "Concrete", "Stomp", "Thump", "Boxer", "Knockout", "Drive", "Pulse", "Beast", "Goliath", "Mammoth", "Titan", "Rumble", "Quake", "Abyss", "Slam", "Smasher", "Crash", "Battering", "Iron", "Lead", "Hammer", "Piston", "Anvil", "Bash", "Batter", "Force"],
        "smooth": ["Warm", "Soft", "Thud", "Puffy", "Dusty", "Tape", "Vinyl", "Cozy", "Muted", "Aura", "Lush", "Gentle", "Float", "Breeze", "Velvet", "Sable", "Glow", "Dusk", "Dawn", "Haze", "Plump", "Pillow", "Cloud", "Swell", "Pulse", "Round", "Tuned", "Deep", "Chill", "Vibe"],
        "clean": ["Punchy", "Click", "Point", "Sharp", "Tight", "Short", "Snap", "Stab", "Laser", "Cyber", "Tech", "Axis", "Grid", "Core", "Limit", "Sonic", "Volt", "Cyber", "Digital", "Precision", "Exact", "Perfect", "Apex", "Vortex", "Sync", "Pulse", "Knock", "Drive", "Focus", "Crisp"]
    },
    "SNARES": {
        "dark": ["Crack", "Slap", "Crisp", "Sharp", "Clack", "Metal", "Whip", "Smack", "Slam", "Shot", "Riot", "Static", "Bullet", "Sniper", "Trigger", "Blade", "Cut", "Slash", "Spit", "Shred", "Bite", "Sting", "Blast", "Explode", "Tear", "Break", "Crush", "Smash", "Rattle", "Clatter"],
        "smooth": ["Dusty", "Tape", "Vinyl", "Soft", "Brushed", "Warm", "Muted", "Lo-Fi", "Lofi", "Aura", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Whisper", "Feather", "Float", "Breeze", "Dusk", "Dawn", "Shimmer", "Glow", "Lush", "Chill", "Vibe", "Subtle", "Gentle", "Mellow", "Quiet"],
        "clean": ["Tight", "Short", "Snap", "Stab", "Click", "Laser", "Cyber", "Tech", "Digital", "Studio", "Plate", "Gate", "Dry", "Acoustic", "Modern", "Perfect", "Precision", "Exact", "Apex", "Vortex", "Sync", "Pulse", "Crisp", "Chirp", "Tink", "Tick", "Clink", "Pop", "Zap", "Volt"]
    },
    "CLAPS": {
        "dark": ["Cave", "Swamp", "Viscera", "Trauma", "Riot", "Static", "Slam", "Smack", "Heavy", "Gritty", "Underground", "Doom", "Toxic", "Sludge", "Reaper", "Abyss", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Explode", "Tear", "Crush", "Blade", "Cut", "Slash", "Spit", "Shred", "Bite"],
        "smooth": ["Room", "Hall", "Ambient", "Soft", "Warm", "Dusty", "Tape", "Vinyl", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Whisper", "Feather", "Float", "Breeze", "Dusk", "Dawn", "Shimmer", "Glow", "Lush", "Chill", "Vibe", "Subtle", "Gentle", "Mellow", "Muted", "Quiet", "Softly"],
        "clean": ["Synix", "Room", "Trap", "Tight", "Short", "Snap", "Stab", "Click", "Laser", "Cyber", "Tech", "Digital", "Studio", "Plate", "Gate", "Dry", "Acoustic", "Modern", "Perfect", "Precision", "Exact", "Apex", "Vortex", "Sync", "Pulse", "Crisp", "Chirp", "Pop", "Zap", "Volt"]
    },
    "HATS": {
        "dark": ["Metal", "Gritty", "Static", "Harsh", "Iron", "Steel", "Rusty", "Riot", "Doom", "Toxic", "Sludge", "Reaper", "Abyss", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Explode", "Tear", "Crush", "Blade", "Cut", "Slash", "Spit", "Shred", "Bite", "Sting", "Blast", "Smash"],
        "smooth": ["Closed", "Open", "Pedal", "Tick", "Tink", "Sizzle", "Crisp", "Bright", "Shine", "Silver", "Gold", "Platinum", "Classic", "Modern", "Airy", "Tight", "Loose", "Short", "Soft", "Whisper", "Dusty", "Tape", "Vinyl", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Breeze", "Float"],
        "clean": ["Tight", "Short", "Tick", "Tink", "Click", "Laser", "Cyber", "Tech", "Digital", "Studio", "Precision", "Exact", "Apex", "Vortex", "Sync", "Pulse", "Crisp", "Chirp", "Pop", "Zap", "Volt", "Clock", "Chink", "Shine", "Silver", "Gold", "Platinum", "Modern", "Dry", "Gate"]
    },
    "LOOPS": {
        "dark": ["Melody", "Synth", "Pluck", "Keys", "Guitar", "Vibe", "Atmosphere", "Chords", "Dream", "Night", "Day", "Sun", "Moon", "Stars", "Cloud", "Rain", "Wind", "Fire", "Water", "Earth", "Abyss", "Phantom", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Doom", "Toxic", "Sludge"],
        "smooth": ["Warmth", "Velvet", "Haze", "Dream", "Clouds", "Swell", "Submerge", "Sunset", "Vibe", "Cozy", "Chill", "Dusk", "Dawn", "Aura", "Static", "Vinyl", "Sable", "Silk", "Lush", "Soft", "Glow", "Breeze", "Float", "Serene", "Mist", "Fade", "Shimmer", "Amber", "Pulse", "Eon"],
        "clean": ["Solid", "Concrete", "Steel", "Anvil", "Piston", "Strike", "Knock", "Impact", "Apex", "Vortex", "Static", "Nova", "Pulse", "Punch", "Click", "Drive", "Stomp", "Hammer", "Force", "Limit", "Axis", "Core", "Cyber", "Grid", "Matrix", "Tech", "Volt", "Wave", "Sonic", "Sync"]
    },
    "PERCS": {
        "dark": ["Rim", "Bongo", "Conga", "Block", "Cowbell", "Shaker", "Tambourine", "Triangle", "Click", "Snap", "Clack", "Tink", "Woodblock", "Maraca", "Cabasa", "Guiro", "Agogo", "Clave", "Castanet", "Tabla", "Abyss", "Phantom", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Doom", "Toxic", "Sludge"],
        "smooth": ["Soft", "Warm", "Dusty", "Tape", "Vinyl", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Whisper", "Feather", "Float", "Breeze", "Dusk", "Dawn", "Shimmer", "Glow", "Lush", "Chill", "Vibe", "Subtle", "Gentle", "Mellow", "Muted", "Quiet", "Softly", "Mellow", "Calm", "Peace"],
        "clean": ["Click", "Snap", "Clack", "Tink", "Tick", "Laser", "Cyber", "Tech", "Digital", "Studio", "Precision", "Exact", "Apex", "Vortex", "Sync", "Pulse", "Crisp", "Chirp", "Pop", "Zap", "Volt", "Rim", "Bongo", "Conga", "Block", "Cowbell", "Shaker", "Tambourine", "Triangle", "Clave"]
    },
    "FX": {
        "dark": ["Riser", "Fall", "Sweep", "Whoosh", "Laser", "Crash", "Reverse", "Vinyl", "Noise", "Glitch", "Stutter", "Swell", "Impact", "Texture", "Drone", "Hum", "Buzz", "Chirp", "Siren", "Alarm", "Abyss", "Phantom", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Doom", "Toxic", "Sludge"],
        "smooth": ["Ambient", "Soft", "Warm", "Dusty", "Tape", "Vinyl", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Whisper", "Feather", "Float", "Breeze", "Dusk", "Dawn", "Shimmer", "Glow", "Lush", "Chill", "Vibe", "Subtle", "Gentle", "Mellow", "Muted", "Quiet", "Softly", "Mellow", "Calm"],
        "clean": ["Laser", "Cyber", "Tech", "Digital", "Studio", "Precision", "Exact", "Apex", "Vortex", "Sync", "Pulse", "Crisp", "Chirp", "Pop", "Zap", "Volt", "Glitch", "Stutter", "Swell", "Impact", "Texture", "Drone", "Hum", "Buzz", "Riser", "Fall", "Sweep", "Whoosh", "Reverse", "Noise"]
    },
    "VOX": {
        "dark": ["Chant", "Vox", "Vocal", "Scream", "Shout", "Cry", "Whisper", "Grunt", "Gasp", "Sigh", "Laugh", "Howl", "Growl", "Roar", "Abyss", "Phantom", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Doom", "Toxic", "Sludge", "Reaper", "Abyss", "Slasher", "Venom", "Hollow", "Creep"],
        "smooth": ["Chant", "Vox", "Vocal", "Soft", "Warm", "Dusty", "Tape", "Vinyl", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Whisper", "Feather", "Float", "Breeze", "Dusk", "Dawn", "Shimmer", "Glow", "Lush", "Chill", "Vibe", "Subtle", "Gentle", "Mellow", "Muted", "Quiet", "Softly"],
        "clean": ["Chant", "Vox", "Vocal", "Laser", "Cyber", "Tech", "Digital", "Studio", "Precision", "Exact", "Apex", "Vortex", "Sync", "Pulse", "Crisp", "Chirp", "Pop", "Zap", "Volt", "Gate", "Dry", "Modern", "Perfect", "Precision", "Exact", "Apex", "Vortex", "Sync", "Pulse", "Crisp"]
    },
    "OTHERS": {
        "dark": ["Sample", "Sound", "OneShot", "Tone", "Note", "Wave", "Signal", "Pulse", "Beep", "Blip", "Noise", "Click", "Pop", "Snap", "Crack", "Hiss", "Hum", "Buzz", "Drone", "Chirp", "Abyss", "Phantom", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Doom", "Toxic", "Sludge"],
        "smooth": ["Sample", "Sound", "OneShot", "Tone", "Note", "Wave", "Signal", "Pulse", "Beep", "Blip", "Soft", "Warm", "Dusty", "Tape", "Vinyl", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Whisper", "Feather", "Float", "Breeze", "Dusk", "Dawn", "Shimmer", "Glow", "Lush", "Chill"],
        "clean": ["Sample", "Sound", "OneShot", "Tone", "Note", "Wave", "Signal", "Pulse", "Beep", "Blip", "Laser", "Cyber", "Tech", "Digital", "Studio", "Precision", "Exact", "Apex", "Vortex", "Sync", "Pulse", "Crisp", "Chirp", "Pop", "Zap", "Volt", "Gate", "Dry", "Modern"]
    },
    "BASSES": {
        "dark": ["Sub", "Low", "Growl", "Reese", "Deep", "Fat", "Thick", "Pluck", "Wobble", "Heavy", "Doom", "Toxic", "Sludge", "Reaper", "Abyss", "Slasher", "Venom", "Hollow", "Creep", "Cinder"],
        "smooth": ["Warmth", "Velvet", "Haze", "Dream", "Clouds", "Swell", "Submerge", "Sunset", "Vibe", "Cozy", "Chill", "Dusk", "Dawn", "Aura", "Static", "Vinyl", "Sable", "Silk", "Lush", "Soft"],
        "clean": ["Solid", "Concrete", "Steel", "Anvil", "Piston", "Strike", "Knock", "Impact", "Apex", "Vortex", "Static", "Nova", "Pulse", "Punch", "Click", "Drive", "Stomp", "Hammer", "Force", "Limit"]
    },
    "BELLS": {
        "dark": ["Ring", "Chime", "Tinkle", "Glass", "Crystal", "Silver", "Ice", "Metallic", "Tone", "Doom", "Toxic", "Sludge", "Reaper", "Abyss", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Grave"],
        "smooth": ["Warm", "Soft", "Muted", "Lo-Fi", "Lofi", "Aura", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Whisper", "Feather", "Float", "Breeze", "Dusk", "Dawn", "Shimmer", "Glow", "Lush"],
        "clean": ["Crisp", "Chirp", "Tink", "Tick", "Clink", "Pop", "Zap", "Volt", "Clock", "Chink", "Shine", "Silver", "Gold", "Platinum", "Modern", "Dry", "Gate", "Apex", "Vortex", "Sync"]
    },
    "KEYS": {
        "dark": ["Piano", "Rhodes", "Organ", "Synth", "Electric", "Classic", "Vibe", "Smooth", "Doom", "Toxic", "Sludge", "Reaper", "Abyss", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Grave"],
        "smooth": ["Warm", "Soft", "Muted", "Lo-Fi", "Lofi", "Aura", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Whisper", "Feather", "Float", "Breeze", "Dusk", "Dawn", "Shimmer", "Glow", "Lush"],
        "clean": ["Solid", "Concrete", "Steel", "Anvil", "Piston", "Strike", "Knock", "Impact", "Apex", "Vortex", "Static", "Nova", "Pulse", "Punch", "Click", "Drive", "Stomp", "Hammer", "Force", "Limit"]
    },
    "LEADS": {
        "dark": ["Lead", "Pluck", "Laser", "Glide", "Cyber", "Pulse", "Volt", "Sharp", "Bright", "Doom", "Toxic", "Sludge", "Reaper", "Abyss", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Grave"],
        "smooth": ["Warm", "Soft", "Muted", "Lo-Fi", "Lofi", "Aura", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Whisper", "Feather", "Float", "Breeze", "Dusk", "Dawn", "Shimmer", "Glow", "Lush"],
        "clean": ["Laser", "Cyber", "Tech", "Digital", "Studio", "Precision", "Exact", "Apex", "Vortex", "Sync", "Pulse", "Crisp", "Chirp", "Pop", "Zap", "Volt", "Glitch", "Stutter", "Swell", "Impact"]
    },
    "PRESETS": {
        "dark": ["Patch", "Preset", "Bank", "Sound", "Synth", "Bass", "Lead", "Pluck", "Doom", "Toxic", "Sludge", "Reaper", "Abyss", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Grave"],
        "smooth": ["Warm", "Soft", "Muted", "Lo-Fi", "Lofi", "Aura", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Whisper", "Feather", "Float", "Breeze", "Dusk", "Dawn", "Shimmer", "Glow", "Lush"],
        "clean": ["Laser", "Cyber", "Tech", "Digital", "Studio", "Precision", "Exact", "Apex", "Vortex", "Sync", "Pulse", "Crisp", "Chirp", "Pop", "Zap", "Volt", "Glitch", "Stutter", "Swell", "Impact"]
    },
    "MIDI": {
        "dark": ["Note", "Chord", "Progression", "Pattern", "Scale", "Melody", "Arrangement", "Composition", "Score", "Doom", "Toxic", "Sludge", "Reaper", "Abyss", "Slasher", "Venom", "Hollow", "Creep", "Cinder", "Grave"],
        "smooth": ["Warm", "Soft", "Muted", "Lo-Fi", "Lofi", "Aura", "Cozy", "Velvet", "Silk", "Sable", "Haze", "Whisper", "Feather", "Float", "Breeze", "Dusk", "Dawn", "Shimmer", "Glow", "Lush"],
        "clean": ["Solid", "Concrete", "Steel", "Anvil", "Piston", "Strike", "Knock", "Impact", "Apex", "Vortex", "Static", "Nova", "Pulse", "Punch", "Click", "Drive", "Stomp", "Hammer", "Force", "Limit"]
    }
}

def get_rebrand_names(category: str, count: int, genre: str, ai_naming: Optional[bool] = None) -> List[str]:
    """Retrieves rebranded sample names, querying AI first if enabled, falling back to local pool."""
    import config
    import random
    
    category_caps = category.upper()
    
    # Dynamic fallback mapping if the custom category is not in FALLBACK_NAMES
    if category_caps not in FALLBACK_NAMES:
        mapped = False
        for kw in ["BASS", "SUB"]:
            if kw in category_caps:
                category_caps = "BASSES"
                mapped = True
                break
        if not mapped:
            for kw in ["BELL"]:
                if kw in category_caps:
                    category_caps = "BELLS"
                    mapped = True
                    break
        if not mapped:
            for kw in ["KEY", "PIANO", "ORGAN", "RHODES"]:
                if kw in category_caps:
                    category_caps = "KEYS"
                    mapped = True
                    break
        if not mapped:
            for kw in ["LEAD", "SYNTH", "PLUCK", "PAD"]:
                if kw in category_caps:
                    category_caps = "LEADS"
                    mapped = True
                    break
        if not mapped:
            for kw in ["PRESET", "PATCH", "BANK", "FXP", "FXB", "FST"]:
                if kw in category_caps:
                    category_caps = "PRESETS"
                    mapped = True
                    break
        if not mapped:
            for kw in ["MIDI", "MID"]:
                if kw in category_caps:
                    category_caps = "MIDI"
                    mapped = True
                    break
        if not mapped:
            category_caps = "OTHERS"
        
    names = []
    
    # 1. Query AI if enabled (pass the actual category for contextual names!)
    ai_enabled = ai_naming if ai_naming is not None else getattr(config, "AI_UNIQUE_NAMING", True)
    if ai_enabled:
        print(f"Querying AI for {count} names for {category} ({genre})...")
        names = query_ai_sample_names(category, count, genre)
        
    # 2. If AI failed/disabled or returned empty, use local fallback pool
    if not names:
        genre_lower = genre.lower()
        if "trap" in genre_lower or "phonk" in genre_lower:
            style = "dark"
        elif "lofi" in genre_lower or "rnb" in genre_lower or "chill" in genre_lower or "soul" in genre_lower:
            style = "smooth"
        else:
            style = "clean"
            
        pool = FALLBACK_NAMES[category_caps][style]
        pool_shuffled = list(pool)
        random.shuffle(pool_shuffled)
        
        while len(names) < count:
            for item in pool_shuffled:
                if len(names) >= count:
                    break
                candidate = item
                idx = 1
                while candidate in names:
                    idx += 1
                    candidate = f"{item} {idx}"
                names.append(candidate)
                
    return names[:count]

def singularize_category(cat: str) -> str:
    """Singularizes a category name in lowercase."""
    cat_lower = cat.lower().strip()
    if cat_lower.endswith("ies"):
        return cat_lower[:-3] + "y"
    if cat_lower.endswith("sses"):
        return cat_lower[:-2]
    if cat_lower.endswith(("ches", "shes", "xes", "zes")):
        return cat_lower[:-2]
    if cat_lower.endswith("s") and not cat_lower.endswith("ss"):
        return cat_lower[:-1]
    return cat_lower

def categorize_sample(filename: str, parent_folder: str) -> str:
    """Categorizes the sample based on filename and folder names (kept for fallback compatibility)."""
    cat, _ = parse_category_and_descriptor(os.path.join(parent_folder, filename))
    return cat.title()

def process_and_rename_kit(root_dir: str, rebranded_name: str = "Resold", genre: str = "Trap", ai_naming: Optional[bool] = None) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Recursively scans files in root_dir:
    1. Keeps only allowed files (audio, presets, MIDI, FLP) and deletes all non-allowed files.
    2. Groups them by parsed category (e.g., 808S, KICKS, custom categories) and extracts descriptors.
    3. Renames the files using the configured template (or AI names) and copies them to 
       flat category folders inside a new root directory named 'REBRANDED_NAME (Produced by Arqive)' in CAPS.
    4. Cleans up empty folders and leftovers.
    """
    import config
    import os
    import shutil
    
    # 1. Walk directory to find all allowed and non-allowed files
    allowed_files_by_cat: Dict[str, List[Tuple[str, str, str]]] = {} # category -> list of (abs_path, filename, descriptor)
    non_allowed_files: List[str] = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Calculate relative path from root_dir
        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == ".":
            rel_dir = ""
            
        for name in filenames:
            fpath = os.path.join(dirpath, name)
            file_ext = os.path.splitext(name)[1].lower()
            if file_ext in ALLOWED_EXTENSIONS:
                cat, desc = parse_category_and_descriptor(rel_dir)
                if cat == "OTHERS":
                    fn_cat, fn_desc = parse_category_and_descriptor(name)
                    if fn_cat != "OTHERS":
                        cat = fn_cat
                        if not desc:
                            desc = fn_desc
                if cat not in allowed_files_by_cat:
                    allowed_files_by_cat[cat] = []
                allowed_files_by_cat[cat].append((fpath, name, desc))
            else:
                non_allowed_files.append(fpath)
                
    # Delete non-allowed files immediately
    for naf in non_allowed_files:
        try:
            os.remove(naf)
        except Exception as e:
            print(f"Error removing non-allowed file {naf}: {e}")
            
    # Create the temporary rebranded directory structure in a separate parent directory
    # to avoid collisions when the input ZIP is already structured as target_root_name.
    clean_rebranded = rebranded_name.replace("Arqive", "").replace("[AQ]", "").strip()
    target_root_name = f"{clean_rebranded.upper()} {genre.upper()} PACK (Produced by Arqive)"
    
    temp_rebranded_parent = root_dir + "_rebranded_temp"
    if os.path.exists(temp_rebranded_parent):
        shutil.rmtree(temp_rebranded_parent)
    os.makedirs(temp_rebranded_parent, exist_ok=True)
    
    temp_rebranded_dir = os.path.join(temp_rebranded_parent, target_root_name)
    os.makedirs(temp_rebranded_dir, exist_ok=True)
    
    final_categories: Dict[str, List[str]] = {}
    final_all_files: List[str] = []
    
    # Process each category
    for cat_caps, files in allowed_files_by_cat.items():
        cat_dir = os.path.join(temp_rebranded_dir, cat_caps)
        os.makedirs(cat_dir, exist_ok=True)
        final_categories[cat_caps] = []
        
        file_count = len(files)
        # Fetch rebranded names if AI naming mode is selected
        ai_names = []
        mode = getattr(config, "REBRAND_NAMING_MODE", "ai_unique_suffix")
        if mode in ["ai_unique_prefix", "ai_unique_suffix"]:
            ai_names = get_rebrand_names(cat_caps, file_count, genre, ai_naming)
            
        for idx, (old_path, filename, descriptor) in enumerate(files, 1):
            file_ext = os.path.splitext(filename)[1].lower()
            base_name = os.path.splitext(filename)[0]
            bpm, key = parse_bpm_key(base_name)
            
            category_clean = singularize_category(cat_caps)
            category_title = category_clean.title()
            desc_clean = descriptor.lower()
            desc_title = descriptor.title()
            
            # Format BPM/Key metadata
            meta = []
            if bpm:
                meta.append(f"{bpm}BPM")
            if key:
                meta.append(key)
            meta_str = " " + " ".join(f"({m})" for m in meta) if meta else ""
            
            # Build rebranded name using template
            if mode == "prefix":
                name_part = f"[AQ] {category_clean}"
                if desc_clean:
                    name_part += f" {desc_clean}"
                name_part += f" {idx:03d}"
            elif mode == "suffix":
                name_part = f"{category_clean}"
                if desc_clean:
                    name_part += f" {desc_clean}"
                name_part += f" {idx:03d} - @aq"
            elif mode == "index_first":
                name_part = f"{idx:03d} {category_title}"
                if desc_title:
                    name_part += f" {desc_title}"
                name_part += " - @aq"
            elif mode == "ai_unique_prefix":
                ai_name = ai_names[idx - 1]
                name_part = f"[AQ] {idx:03d} {category_title} {ai_name}"
            elif mode == "ai_unique_suffix":
                ai_name = ai_names[idx - 1]
                name_part = f"{idx:03d} {category_title} {ai_name} - @aq"
            else:
                name_part = f"[AQ] {category_clean} {idx:03d}"
                
            new_name = name_part + meta_str + file_ext
            new_name = new_name.replace("  ", " ").strip()  # clean any double spacing
            new_path = os.path.join(cat_dir, new_name)
            
            try:
                shutil.copy2(old_path, new_path)
                # Compute the final path in root_dir since we'll rename temp_rebranded_parent to root_dir
                final_path = os.path.join(root_dir, target_root_name, cat_caps, new_name)
                final_categories[cat_caps].append(final_path)
                final_all_files.append(final_path)
            except Exception as e:
                print(f"Error copying renamed file {old_path} to {new_path}: {e}")
                
    # Delete the entire original root_dir
    try:
        shutil.rmtree(root_dir)
    except Exception as e:
        print(f"Error removing original root_dir: {e}")
        
    # Move temp_rebranded_parent to root_dir
    try:
        shutil.move(temp_rebranded_parent, root_dir)
    except Exception as e:
        print(f"Error moving rebranded folder: {e}")
            
    return final_categories, final_all_files

def select_preview_showcase(categories: Dict[str, List[str]], max_per_cat: int = 5) -> List[Tuple[str, str]]:
    """
    Selects up to max_per_cat samples from each category to form a preview.
    Filters out non-audio files (presets, MIDIs, FLPs) and only includes playable audio extensions.
    Returns list of tuples: (file_path, category_name)
    """
    showcase = []
    # Order of showcase playback: LOOPS first, then 808S, KICKS, SNARES, CLAPS, HATS, PERCS, FX, VOX, OTHERS
    order = ["LOOPS", "808S", "KICKS", "SNARES", "CLAPS", "HATS", "PERCS", "FX", "VOX", "OTHERS"]
    
    # Process standard categories in defined order
    for cat in order:
        if cat in categories:
            audio_files = [f for f in categories[cat] if os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS]
            selected = audio_files[:max_per_cat]
            for f in selected:
                showcase.append((f, cat))
                
    # Process any remaining custom/dynamic categories (alphabetically)
    for cat in sorted(categories.keys()):
        if cat not in order:
            audio_files = [f for f in categories[cat] if os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS]
            selected = audio_files[:max_per_cat]
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

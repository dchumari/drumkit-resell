import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Inject WinGet links path at runtime to ensure newly installed FFmpeg is found
winget_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links")
if os.path.exists(winget_path) and winget_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = os.environ.get("PATH", "") + os.path.pathsep + winget_path

# Dynamic check inside WinGet package directories (self-healing)
import glob
user_local = os.getenv("LOCALAPPDATA", "")
if user_local:
    winget_packages = os.path.join(user_local, "Microsoft", "WinGet", "Packages")
    if os.path.exists(winget_packages):
        ffmpeg_bins = glob.glob(os.path.join(winget_packages, "Gyan.FFmpeg*", "*", "bin"))
        for bin_dir in ffmpeg_bins:
            if os.path.isdir(bin_dir) and bin_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_dir + os.path.pathsep + os.environ.get("PATH", "")

def load_env_file():
    """Manually parses a local .env file in the root directory if it exists."""
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    os.environ[key] = val

load_env_file()

# API Keys & Credentials
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "script:drumkit-reseller:v1.0 (by /u/arqive-developer)")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
LOGGING_BOT_TOKEN = os.getenv("LOGGING_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")  # Target chat ID for logging bot

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")

# Telegram Channel Configurations
CHANNEL_A_CHAT_ID = os.getenv("CHANNEL_A_CHAT_ID", "")  # Premium subscription channel/group
CHANNEL_B_CHAT_ID = os.getenv("CHANNEL_B_CHAT_ID", "")  # Storefront channel/group

# Promotional campaign day
FREE_DAY = os.getenv("FREE_DAY", "Friday")

# Star Pricing Brackets based on file size in megabytes
PRICE_BRACKETS = [
    {"max_size_mb": 100, "price": 150},
    {"max_size_mb": 500, "price": 300},
    {"max_size_mb": 1500, "price": 500},
    {"max_size_mb": float("inf"), "price": 750}
]

# Genre-to-Topic Thread Map (message_thread_id) for Channels A & B
# Customize these values based on your Telegram supergroup topic IDs.
GENRE_TOPICS_A = {
    "Trap": int(os.getenv("TOPIC_A_TRAP", "2")),
    "RnB": int(os.getenv("TOPIC_A_RNB", "3")),
    "Lofi": int(os.getenv("TOPIC_A_LOFI", "4")),
    "Phonk": int(os.getenv("TOPIC_A_PHONK", "5")),
    "Hip-Hop": int(os.getenv("TOPIC_A_HIPHOP", "6")),
    "Default": int(os.getenv("TOPIC_A_DEFAULT", "1"))
}

GENRE_TOPICS_B = {
    "Trap": int(os.getenv("TOPIC_B_TRAP_HIPHOP", "2")),
    "Hip-Hop": int(os.getenv("TOPIC_B_TRAP_HIPHOP", "2")),
    "RnB": int(os.getenv("TOPIC_B_RNB", "8")),
    "Lofi": int(os.getenv("TOPIC_B_LOFI", "13")),
    "Phonk": int(os.getenv("TOPIC_B_PHONK", "11")),
    "Reggaeton": int(os.getenv("TOPIC_B_REGGAETON", "6")),
    "House": int(os.getenv("TOPIC_B_HOUSE_MUSIC", "4")),
    "Default": int(os.getenv("TOPIC_B_DEFAULT", "1"))
}

# Visual Styling per Genre (RGB Gradients and asset overlay files)
GENRE_COLORS = {
    "Trap": {
        "bg_gradient": ((15, 10, 25), (45, 15, 80)),       # Dark violet to neon purple
        "text_color": (0, 240, 255),                       # Bright Cyan
        "border_color": (30, 200, 220),
        "overlay": "grid.png"                              # Overlay asset file name
    },
    "RnB": {
        "bg_gradient": ((30, 10, 15), (90, 25, 45)),       # Deep velvet to warm pinkish red
        "text_color": (255, 182, 193),                     # Light pink
        "border_color": (210, 105, 120),
        "overlay": "waves.png"
    },
    "Lofi": {
        "bg_gradient": ((10, 15, 25), (35, 60, 85)),       # Dark blue-grey to warm pastel blue
        "text_color": (240, 220, 180),                     # Retro cream/sand
        "border_color": (160, 140, 100),
        "overlay": "cassette.png"
    },
    "Phonk": {
        "bg_gradient": ((5, 5, 5), (40, 0, 10)),           # Glitch black to dark red
        "text_color": (255, 30, 30),                       # Gritty red
        "border_color": (180, 20, 20),
        "overlay": "vinyl.png"
    },
    "Hip-Hop": {
        "bg_gradient": ((15, 15, 15), (60, 50, 40)),       # Street grey to warm gold/bronze
        "text_color": (255, 215, 0),                       # Gold
        "border_color": (200, 170, 30),
        "overlay": "grid.png"
    },
    "Reggaeton": {
        "bg_gradient": ((40, 20, 10), (100, 40, 20)),      # Dark amber to warm orange
        "text_color": (255, 180, 0),                       # Bright Gold/Orange
        "border_color": (220, 150, 10),
        "overlay": "vinyl.png"
    },
    "House": {
        "bg_gradient": ((10, 10, 30), (20, 30, 90)),       # Deep space blue to electric blue
        "text_color": (0, 255, 180),                       # Neon Teal
        "border_color": (10, 220, 150),
        "overlay": "grid.png"
    },
    "Default": {
        "bg_gradient": ((10, 8, 14), (60, 50, 70)),        # Original Arqive theme colors
        "text_color": (255, 160, 30),
        "border_color": (160, 150, 170),
        "overlay": ""
    }
}

MULTIPLE_STYLES = {
    "rounded_sidebar": {
        "font_family": "Mulish",
        "bg_gradient": ((30, 20, 50), (10, 8, 20)),
        "text_color": (162, 130, 255),
        "border_color": (80, 60, 140),
        "secondary_color": (255, 255, 255),
        "active_badge_bg": (162, 130, 255),
        "active_badge_fg": (10, 8, 20),
        "rounded_corners": 20,
        "card_opacity": 15,
        "wave_color": "0xa282ff"
    },
    "friendly_glass": {
        "font_family": "Nunito",
        "bg_gradient": ((40, 25, 10), (15, 10, 5)),
        "text_color": (255, 152, 0),
        "border_color": (160, 100, 30),
        "secondary_color": (255, 255, 255),
        "active_badge_bg": (255, 152, 0),
        "active_badge_fg": (255, 255, 255),
        "rounded_corners": 16,
        "card_opacity": 20,
        "wave_color": "0xff9800"
    },
    "liquid_glass": {
        "font_family": "Nunito",
        "bg_gradient": ((45, 10, 30), (15, 5, 10)),
        "text_color": (255, 42, 133),
        "border_color": (150, 30, 80),
        "secondary_color": (255, 255, 255),
        "active_badge_bg": (255, 42, 133),
        "active_badge_fg": (255, 255, 255),
        "rounded_corners": 35,
        "card_opacity": 22,
        "wave_color": "0xff2a85"
    },
    "pastel_minimalist": {
        "font_family": "Mulish",
        "bg_gradient": ((0, 150, 130), (0, 60, 50)),
        "text_color": (0, 191, 165),
        "border_color": (255, 255, 255),
        "secondary_color": (255, 255, 255),
        "active_badge_bg": (255, 255, 255),
        "active_badge_fg": (0, 191, 165),
        "rounded_corners": 28,
        "card_opacity": 250,
        "wave_color": "0x00bfa5"
    },
    "neon_sunset": {
        "font_family": "Nunito",
        "bg_gradient": ((15, 10, 25), (45, 15, 80)),
        "text_color": (255, 0, 127),
        "border_color": (255, 255, 0),
        "secondary_color": (255, 123, 0),
        "active_badge_bg": (255, 255, 0),
        "active_badge_fg": (0, 0, 0),
        "rounded_corners": 20,
        "card_opacity": 255,
        "wave_color": "0xffff00"
    },
    "floating_badge": {
        "font_family": "Nunito",
        "bg_gradient": ((10, 20, 30), (5, 10, 15)),
        "text_color": (0, 242, 254),
        "border_color": (30, 150, 160),
        "secondary_color": (255, 255, 255),
        "active_badge_bg": (0, 242, 254),
        "active_badge_fg": (10, 20, 30),
        "rounded_corners": 20,
        "card_opacity": 20,
        "wave_color": "0x00f2fe"
    },
    "frosted_bubble": {
        "font_family": "Mulish",
        "bg_gradient": ((15, 25, 20), (5, 10, 8)),
        "text_color": (255, 179, 0),
        "border_color": (255, 179, 0),
        "secondary_color": (255, 94, 151),
        "active_badge_bg": (255, 94, 151),
        "active_badge_fg": (255, 255, 255),
        "rounded_corners": 30,
        "card_opacity": 18,
        "wave_color": "0xffb300"
    },
    "liquid_sunset": {
        "font_family": "Nunito",
        "bg_gradient": ((20, 10, 30), (5, 2, 10)),
        "text_color": (255, 138, 0),
        "border_color": (255, 0, 127),
        "secondary_color": (255, 255, 255),
        "active_badge_bg": (255, 0, 127),
        "active_badge_fg": (255, 255, 255),
        "rounded_corners": 24,
        "card_opacity": 15,
        "wave_color": "0xff8a00"
    },
    "asymmetric_float": {
        "font_family": "Mulish",
        "bg_gradient": ((25, 20, 45), (10, 8, 20)),
        "text_color": (162, 130, 255),
        "border_color": (162, 130, 255),
        "secondary_color": (255, 255, 255),
        "active_badge_bg": (162, 130, 255),
        "active_badge_fg": (10, 8, 20),
        "rounded_corners": 28,
        "card_opacity": 20,
        "wave_color": "0xa282ff"
    }
}

# Alias mapping asymmetric_flow to asymmetric_float
MULTIPLE_STYLES["asymmetric_flow"] = MULTIPLE_STYLES["asymmetric_float"]

GENRE_STYLE_MAP = {
    "RnB": "pastel_minimalist",
    "Trap": "liquid_glass",
    "Lofi": "pastel_minimalist",
    "Phonk": "rounded_sidebar",
    "Hip-Hop": "rounded_sidebar",
    "Reggaeton": "liquid_glass",
    "House": "liquid_glass",
    "Default": "asymmetric_float"
}

COLOR_MAP = {
    "red": (255, 30, 30),
    "orange": (255, 127, 0),
    "yellow": (255, 220, 0),
    "green": (50, 220, 80),
    "mint": (0, 240, 160),
    "cyan": (0, 220, 255),
    "blue": (0, 127, 255),
    "purple": (162, 130, 255),
    "pink": (255, 0, 127),
    "magenta": (255, 0, 127),
    "white": (245, 245, 250),
}

def resolve_custom_color_palette(color_str: str):
    """
    Parses a color override string (hex, named, or 'random') and generates
    a cohesive 3-color palette (bg_gradient_start, bg_gradient_end, accent_text).
    """
    import random
    color_str = color_str.strip().lower()
    
    # 1. Handle random color generation
    if color_str == "random":
        # Pick a random predefined color name
        color_str = random.choice(list(COLOR_MAP.keys()))
        
    accent = None
    
    # 2. Parse hex color
    if color_str.startswith("#"):
        hex_val = color_str.lstrip("#")
        try:
            accent = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            accent = (255, 160, 30)  # Default fallback orange
            
    # 3. Parse named color
    if not accent:
        accent = COLOR_MAP.get(color_str)
        
    # 4. Fallback if not found
    if not accent:
        accent = (255, 160, 30)
        
    # 5. Derive gradient backgrounds (cohesive dark tint)
    # Background start: 20% of accent brightness
    color1 = (max(8, accent[0] // 5), max(8, accent[1] // 5), max(8, accent[2] // 5))
    # Background end: 8% of accent brightness (near black)
    color2 = (max(4, accent[0] // 12), max(4, accent[1] // 12), max(4, accent[2] // 12))
    
    return (color1, color2, accent)



# Affiliate VST/Sample pack marketing links mapped to genre
AFFILIATE_LINKS = {
    "Trap": "🔥 Recommended Trap VST: https://affiliate.example.com/synth-vst\n🔊 Best Saturation Plugin: https://affiliate.example.com/sat-plugin",
    "RnB": "🎹 Premium R&B Keys VST: https://affiliate.example.com/rnb-keys\n🎛️ Silk Vocal Compressor: https://affiliate.example.com/vocal-comp",
    "Lofi": "📼 Vintage Tape Machine Emulator: https://affiliate.example.com/tape-emu\n🎸 Lo-Fi Guitar Chords MIDI: https://affiliate.example.com/lofi-midi",
    "Phonk": "🎛️ Hard Clipper Maximizer: https://affiliate.example.com/clipper\n🥁 Aggressive Cowbell Samples: https://affiliate.example.com/cowbell-kit",
    "Hip-Hop": "🎧 Vintage MPC Sampler emulation: https://affiliate.example.com/mpc-sampler\n🎹 BoomBap Chord Progression MIDI: https://affiliate.example.com/boombap-midi",
    "Reggaeton": "💃 Premium Reggaeton VST & MIDI: https://affiliate.example.com/reggaeton",
    "House": "🎧 Electro/House Synth Plugin: https://affiliate.example.com/house-synth",
    "Default": "🎹 Best All-in-One DAW Controller: https://affiliate.example.com/daw-midi"
}

# Default Active Coupons (OFF30 gives 30% discount, OFF50 gives 50% discount)
# Struct: "CODE": {"pct": discount_percentage, "max_uses": maximum_uses_per_user}
COUPON_CODES = {
    "OFF30": {"pct": 30, "max_uses": 1},
    "OFF50": {"pct": 50, "max_uses": 1},
    "WELCOME10": {"pct": 10, "max_uses": 3}
}

# Static YouTube Title Template
YT_TITLE_TEMPLATE = "*FREE* {rebranded_name} {genre} Drum Kit (Direct Download)"

# Static YouTube Description Template
STATIC_DESC_TEMPLATE = """📦 ARQIVE DRUMKIT RELEASE: {pack_name}

Checkout/Download Links:
🔗 Buy This Kit directly on Telegram: {tg_invoice_link}
✨ Subscribe to our Premium Channel to download ALL kits for free: {tg_subscription_link}

---
📂 PACK CONTENTS:
{pack_contents}

---
{affiliate_recommendations}

---
Note: Compiled and presented by Arqive Collection. All files are royalty-free. Pinned comment contains direct checkout links for mobile users.
"""

# Rebranding Naming Configurations
# Modes: 'prefix', 'suffix', 'index_first', 'ai_unique_prefix', 'ai_unique_suffix'
REBRAND_NAMING_MODE = os.getenv("REBRAND_NAMING_MODE", "ai_unique_suffix")
AI_UNIQUE_NAMING = os.getenv("AI_UNIQUE_NAMING", "True").lower() == "true"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")

# Preview Showreel Durations (in seconds)
PREVIEW_LOOP_DURATION = float(os.getenv("PREVIEW_LOOP_DURATION", "12.0"))
PREVIEW_ONESHOT_MIN_DURATION = float(os.getenv("PREVIEW_ONESHOT_MIN_DURATION", "1.0"))
PREVIEW_ONESHOT_MAX_DURATION = float(os.getenv("PREVIEW_ONESHOT_MAX_DURATION", "2.5"))

# Minimum number of allowed samples in a pack to process
MIN_PACK_SAMPLES = int(os.getenv("MIN_PACK_SAMPLES", "5"))

def load_dynamic_genres():
    """Loads dynamically created genres from data/dynamic_genres.json and merges them."""
    import json
    path = os.path.join(DATA_DIR, "dynamic_genres.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for gname, info in data.items():
                if "bg_gradient" in info:
                    bg_grad = tuple(tuple(c) for c in info["bg_gradient"])
                    txt_c = tuple(info["text_color"])
                    border_c = tuple(info["border_color"])
                    GENRE_COLORS[gname] = {
                        "bg_gradient": bg_grad,
                        "text_color": txt_c,
                        "border_color": border_c,
                        "overlay": info.get("overlay", "")
                    }
                if "topic_a" in info:
                    GENRE_TOPICS_A[gname] = info["topic_a"]
                if "topic_b" in info:
                    GENRE_TOPICS_B[gname] = info["topic_b"]
                if "affiliate" in info:
                    AFFILIATE_LINKS[gname] = info["affiliate"]
        except Exception as e:
            print(f"Error loading dynamic_genres.json: {e}")

# Initial load
load_dynamic_genres()



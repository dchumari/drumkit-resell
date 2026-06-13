import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")

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
                    if key not in os.environ:
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

# Static YouTube Description Template
STATIC_DESC_TEMPLATE = """📦 ARQIVE DRUMKIT RE-RELEASE: {pack_name}

Checkout/Download Links:
🔗 Buy This Kit directly on Telegram: {tg_invoice_link}
✨ Subscribe to our Premium Channel to download ALL kits for free: {tg_subscription_link}

---
📂 PACK CONTENTS:
{pack_contents}

---
{affiliate_recommendations}

---
Note: Re-branded and compiled automatically by Arqive Reseller. All files are royalty-free. Pinned comment contains direct checkout links for mobile users.
"""

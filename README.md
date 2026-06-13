# Arqive Drumkit Reseller Automation

An autonomous AI-powered pipeline to scrape, rebrand, package, and resell drumkits from Reddit's `/r/Drumkits` to Telegram and YouTube.

---

## Features

- **RSS-Based Scraper**: Fetches new posts from `/r/Drumkits` via the XML Atom RSS feed to bypass Reddit's anti-scraping blocks, with an automatic JSON fallback.
- **DeepSeek AI Rebranding**: Generates unique, premium, single-word names and categorizes drumkits into genres (Trap, RnB, Lofi, Phonk, Hip-Hop, House, Reggaeton) using DeepSeek models.
- **Brand Whitewashing**: Strips original manufacturer names and metadata tags from sample audio files, renaming files systematically to preserve BPM/Key descriptors.
- **Procedural Artwork**: Generates custom colored vector cover art and projects it onto a 3D perspective box mockup.
- **Watermarked Showcase Mix**: Compiles a preview audio showreel overlayed with voice-tag watermarks.
- **Video Showreels (FFmpeg)**: Automates compiling a landscape 16:9 YouTube showcase video (with active subtitle tracklists and waveforms) and a vertical 9:16 Reel/Shorts video.
- **Storefront Payment Bot**: Runs a 24/7 Telegram bot (`src/bot.py`) that handles Stars-based checkout, subscription invoices, coupon codes, and file delivery.
- **YouTube and Telegram Publishers**: Uploads showcase videos to YouTube with automated descriptions/tags and posts storefront interactive invoices in targeted Telegram threads.

---

## Project Structure

```
d:/Projects/AUTOMATIONS/ALL/DRUMKIT-RESELL/
├── src/                          # Core Python source files
│   ├── config.py                 # Central config and path builder
│   ├── pipeline.py               # Main scraper orchestration pipeline & queue loop
│   ├── bot.py                    # 24/7 transaction checkout & subscription bot
│   ├── audio_processor.py        # Brand whitewashing, categorization, & zipping
│   ├── cover_generator.py        # Procedural cover art generator
│   ├── mockup_generator.py       # 3D mockup box generator
│   ├── video_generator.py        # FFmpeg waveform & showreel compile utility
│   ├── downloader.py             # Google Drive, Mega, Mediafire downloader
│   ├── youtube_uploader.py       # YouTube Data API OAuth uploader
│   ├── telegram_publisher.py     # Local Bot API storefront invoice publisher
│   ├── notifier.py               # Telegram error logging dispatcher
│   └── test_all.py               # Self-test validation suite
├── data/                         # Database and tracking registries
│   ├── packs.json                # Completed release database
│   ├── scraped_queue.json        # Reddit scraping queue database
│   └── processed_links.txt       # Duplicate scraper registry
├── assets/                       # Assets pool (watermarks, overlays, overlays)
└── output/                       # Output directory for locally processed packs
```

---

## Getting Started

### Prerequisites

Ensure you have **Python 3.12+**, **uv**, and **FFmpeg** installed on your system.
FFmpeg paths are dynamically scanned and loaded at runtime on Windows (winget directories).

---

## Execution Guide

### 1. Local Analysis Mode (Default Run)
To scrape `/r/Drumkits`, download, rebrand, and compile visual/audio assets locally **without publishing** or editing databases:
```powershell
uv run python src/pipeline.py
```
*Outputs are saved to:* `output/Arqive_<Name>/`

### 2. Direct Offline Mock Generation
Generate synthetic drumkit files locally and test the entire cover, audio, and FFmpeg video pipeline offline:
```powershell
uv run python src/pipeline.py --mock
```

### 3. Process a Specific Local ZIP File
Manually package, rebrand, and generate showreels for a local ZIP archive:
```powershell
uv run python src/pipeline.py --zip "C:\path\to\pack.zip"
```
Force a specific name and genre:
```powershell
uv run python src/pipeline.py --zip "C:\path\to\pack.zip" --name "Helix" --genre "Lofi"
```

### 4. Process a Direct Download Link
```powershell
uv run python src/pipeline.py --url "https://www.mediafire.com/file/example/Kit.zip/file"
```

### 5. Custom Subreddit Scraping
```powershell
uv run python src/pipeline.py --subreddit "LofiProduction"
```

### 6. Production Automated Release
To fetch new posts, process them, and upload them directly to Telegram Channels and YouTube:
```powershell
uv run python src/pipeline.py --upload
```

### 7. Storefront Bot
To run the Telegram storefront payment checkout bot:
```powershell
uv run python src/bot.py
```

### 8. Run Verification Tests
```powershell
uv run python src/test_all.py
```

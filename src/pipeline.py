import os
import re
import sys
import json
import random
import shutil
import datetime
import subprocess
import urllib.request
import urllib.parse
from typing import List, Optional, Tuple

import config
import notifier
import downloader
import audio_processor
import cover_generator
import mockup_generator
import video_generator
import youtube_uploader
import telegram_publisher

PROCESSED_LINKS_FILE = os.path.join(config.DATA_DIR, "processed_links.txt")
QUEUE_FILE = os.path.join(config.DATA_DIR, "scraped_queue.json")
PACKS_FILE = os.path.join(config.DATA_DIR, "packs.json")

def load_processed_links() -> set:
    """Loads the set of processed Reddit post IDs."""
    if not os.path.exists(PROCESSED_LINKS_FILE):
        return set()
    with open(PROCESSED_LINKS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_processed_link(reddit_id: str):
    """Saves a post ID to processed_links.txt."""
    with open(PROCESSED_LINKS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{reddit_id}\n")

def load_queue() -> List[dict]:
    """Loads the scraped links queue."""
    if not os.path.exists(QUEUE_FILE):
        return []
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_queue(queue: List[dict]):
    """Saves the scraped links queue."""
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=4)

def load_packs() -> List[dict]:
    """Loads the registry of completed packs."""
    if not os.path.exists(PACKS_FILE):
        return []
    try:
        with open(PACKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_packs(packs: List[dict]):
    """Saves the registry of completed packs."""
    with open(PACKS_FILE, "w", encoding="utf-8") as f:
        json.dump(packs, f, indent=4)

def scrape_reddit_links() -> int:
    """
    Scrapes r/drumkit hot page and appends new Drive/Mega/Mediafire links 
    to scraped_queue.json if not already processed.
    Returns the number of new links added.
    """
    print("Scraping r/drumkit for download links...")
    url = "https://www.reddit.com/r/drumkit/hot.json?limit=30"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": config.REDDIT_USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Failed to fetch Reddit hot page: {e}")
        return 0

    processed = load_processed_links()
    queue = load_queue()
    queued_urls = {item["url"] for item in queue}
    
    new_adds = 0
    posts = res_data.get("data", {}).get("children", [])
    
    for post in posts:
        pdata = post.get("data", {})
        pid = pdata.get("id")
        title = pdata.get("title", "")
        selftext = pdata.get("selftext", "")
        post_url = pdata.get("url", "")
        
        if pid in processed:
            continue
            
        # Scan selftext and URL for download links
        found_links = []
        for text in [selftext, post_url]:
            # Regex find url patterns
            links = re.findall(r'https?://[^\s()<>]+', text)
            for link in links:
                ltype = downloader.get_link_type(link)
                if ltype != "unsupported" and link not in queued_urls:
                    found_links.append((link, ltype))
                    
        # If we found any valid link, add the post to the queue
        if found_links:
            # We take the first found link for simplicity
            target_link, ltype = found_links[0]
            queue.append({
                "reddit_id": pid,
                "title": title,
                "description": selftext[:500],
                "url": target_link,
                "host": ltype,
                "date_added": datetime.datetime.utcnow().isoformat()
            })
            queued_urls.add(target_link)
            new_adds += 1
            print(f"Queued new pack: {title} ({ltype})")
            
    if new_adds > 0:
        save_queue(queue)
        
    print(f"Scrape completed. Added {new_adds} new links to queue.")
    return new_adds

def query_deepseek_rebrand(title: str, desc: str) -> Tuple[str, str]:
    """Queries OpenRouter to generate a unique single-word rebranded name and genre."""
    if not config.OPENROUTER_API_KEY:
        raise ValueError("OpenRouter API key is missing.")
        
    url = f"{config.OPENROUTER_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/arqive-developer/drumkit-reseller",
    }
    
    prompt = (
        f"Generate a rebranded identity for this drumkit. Original title: '{title}'. Description: '{desc}'.\n"
        f"Instructions:\n"
        f"1. Generate a single-word or short, premium, unique name (e.g. 'Vortex', 'Apex', 'Ember').\n"
        f"2. Classify the genre as one of: Trap, RnB, Lofi, Phonk, Hip-Hop, Reggaeton, House. Default to Trap.\n"
        f"Output MUST be in strict JSON format like this: {{\"name\": \"Apex\", \"genre\": \"Trap\"}}"
    )
    
    payload = {
        "model": "deepseek/deepseek-v4-flash",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}]
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as res:
        res_data = json.loads(res.read().decode("utf-8"))
        content = res_data["choices"][0]["message"]["content"].strip()
        parsed = json.loads(content)
        return parsed["name"], parsed["genre"]

def get_fallback_rebrand(title: str) -> Tuple[str, str]:
    """Local fallback when OpenRouter API fails."""
    # Deduce genre by scanning title keywords
    title_lower = title.lower()
    genre = "Trap"
    if "rnb" in title_lower or "r&b" in title_lower or "soul" in title_lower:
        genre = "RnB"
    elif "lofi" in title_lower or "lo-fi" in title_lower or "chill" in title_lower:
        genre = "Lofi"
    elif "phonk" in title_lower or "drift" in title_lower:
        genre = "Phonk"
    elif "hiphop" in title_lower or "hip hop" in title_lower or "boom" in title_lower:
        genre = "Hip-Hop"
    elif "reggaeton" in title_lower or "afrobeats" in title_lower or "latin" in title_lower:
        genre = "Reggaeton"
    elif "house" in title_lower or "edm" in title_lower or "electronic" in title_lower or "techno" in title_lower:
        genre = "House"
        
    # Generate random name
    prefix_names = ["Vortex", "Apex", "Aura", "Dusk", "Dawn", "Static", "Cinder", "Pulse", "Eon", "Nova"]
    rebranded_name = f"{random.choice(prefix_names)} {random.randint(10, 99)}"
    return rebranded_name, genre

def commit_git_changes(message: str):
    """Commits and pushes updated tracking files to the repository."""
    try:
        subprocess.run(["git", "add", PROCESSED_LINKS_FILE, QUEUE_FILE, PACKS_FILE], check=True)
        # Check if there are changes to commit
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", message], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("Successfully pushed database updates to GitHub.")
        else:
            print("No database changes to commit.")
    except Exception as e:
        print(f"Git push failed: {e}")

def run_throwback_release():
    """Runs a Vault/Throwback release using a highly rated old pack."""
    print("Scraped queue is empty. Running Throwback Release workflow...")
    packs = load_packs()
    if not packs:
        print("No completed packs available for Throwback Release. Skipping run.")
        return
        
    # Filter for packs with rating >= 4.0 or pick randomly if no ratings exist
    candidates = [p for p in packs if p.get("rating", 0.0) >= 4.0]
    if not candidates:
        candidates = packs
        
    old_pack = random.choice(candidates)
    print(f"Selected old pack for Vault Release: {old_pack['name']} ({old_pack['genre']})")
    
    # We will re-generate the cover with a fresh procedurally generated color tint
    temp_dir = os.path.join(config.BASE_DIR, "temp_throwback")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        cover_path = os.path.join(temp_dir, "cover.png")
        mockup_path = os.path.join(temp_dir, "mockup.png")
        overlay_path = os.path.join(temp_dir, "overlay.png")
        audio_path = os.path.join(temp_dir, "preview.mp3")
        srt_path = os.path.join(temp_dir, "subtitles.srt")
        video_path = os.path.join(temp_dir, "video.mp4")
        shorts_path = os.path.join(temp_dir, "shorts.mp4")
        
        # 1. Regenerate visual assets with fresh random colors
        rebranded_name = f"[VAULT] {old_pack['name']}"
        cover_generator.generate_cover_art(rebranded_name, old_pack["genre"], cover_path)
        mockup_generator.generate_3d_mockup(cover_path, mockup_path, rebranded_name, old_pack["genre"])
        
        # 2. Extract mock preview markers from the old pack if saved, otherwise mock it
        markers = old_pack.get("markers", [])
        if not markers:
            markers = [{"name": "Premium Loops", "category": "Loops", "start": 0.0, "end": 15.0}]
            
        # Draw tracklist overlay image
        video_generator.create_tracklist_overlay(rebranded_name, old_pack["genre"], markers, overlay_path)
        video_generator.create_srt_file(markers, srt_path)
        
        # Mock download a short test sound or just compile from a placeholder
        # In a real vault run, we download the original file_id or reuse local cached files.
        # However, to be 100% robust, since we don't have the original samples locally,
        # we can download the document using the bot API to get the audio preview!
        # For simplicity, we assume we have a fallback loop or generate a simple preview.
        # In this workflow, we will check if the old preview audio is available on YouTube or re-compile.
        # Since compile requires files, we can download the file from Telegram using the file_id!
        # Yes! The local Bot API allows downloading files via:
        # http://localhost:8081/bot<token>/getFile?file_id=<file_id>
        # Let's write a simple download helper for file_id to download the ZIP, extract it, and compile!
        local_zip = os.path.join(temp_dir, "old_kit.zip")
        print(f"Downloading old pack ZIP from Telegram using file_id: {old_pack['file_id']}")
        dl_url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getFile"
        # Since the bot is running, we can check file path
        req = urllib.request.Request(dl_url, data=urllib.parse.urlencode({"file_id": old_pack["file_id"]}).encode())
        # Wait, if local Bot API server is running, we can download it directly from localhost:8081
        req_local = urllib.request.Request(f"{telegram_publisher.LOCAL_BOT_API_URL}/bot{config.TELEGRAM_BOT_TOKEN}/getFile?file_id={old_pack['file_id']}")
        
        # Pull file path from response
        with urllib.request.urlopen(req_local, timeout=20) as res:
            res_json = json.loads(res.read().decode())
            file_path_tg = res_json["result"]["file_path"]
            
        # Download the file bytes from local server
        shutil.copy(file_path_tg, local_zip)
        
        # Process and compile just like normal!
        ext_dir = os.path.join(temp_dir, "extracted")
        audio_processor.unzip_pack(local_zip, ext_dir)
        cats, all_files = audio_processor.process_and_rename_kit(ext_dir)
        showcase = audio_processor.select_preview_showcase(cats)
        
        voice_tag = os.path.join(config.ASSETS_DIR, "voice_tag.wav")
        video_generator.compile_preview_audio(showcase, audio_path, voice_tag)
        video_generator.compile_video_16_9(audio_path, mockup_path, overlay_path, video_path, old_pack["genre"], markers, srt_path)
        video_generator.compile_video_9_16_shorts(audio_path, mockup_path, shorts_path, old_pack["genre"], rebranded_name)
        
        # 3. Publish to YouTube
        yt_token = youtube_uploader.get_access_token()
        yt_tags = youtube_uploader.generate_tags_with_deepseek(rebranded_name, old_pack["genre"])
        
        desc = config.STATIC_DESC_TEMPLATE.format(
            pack_name=rebranded_name,
            tg_invoice_link=old_pack.get("tg_invoice_link", "https://t.me/arqive"),
            tg_subscription_link=f"https://t.me/{telegram_publisher.get_bot_username(config.TELEGRAM_BOT_TOKEN)}",
            pack_contents=f"Vault Throwback Release of {old_pack['name']} (Genre: {old_pack['genre']})",
            affiliate_recommendations=config.AFFILIATE_LINKS.get(old_pack["genre"], "")
        )
        
        vid_id = youtube_uploader.upload_video(video_path, f"[VAULT RELEASE] {rebranded_name} [FREE]", desc, yt_tags, yt_token)
        youtube_uploader.add_comment_to_video(vid_id, f"📥 Get this Vault release here: {old_pack.get('tg_invoice_link')}", yt_token)
        
        # 4. Post New Storefront Invoice on Channel B referencing the old file_id
        # (No need to re-upload the ZIP to Telegram, we already have the file_id!)
        bot_uname = telegram_publisher.get_bot_username(config.TELEGRAM_BOT_TOKEN)
        thread_id = config.GENRE_TOPICS_B.get(old_pack["genre"], config.GENRE_TOPICS_B["Default"])
        
        invoice_desc = f"📼 [VAULT THROWBACK] {rebranded_name}\nOne of our top-rated classic kits is back with a fresh layout. Download now!"
        telegram_publisher.publish_invoice(
            config.TELEGRAM_BOT_TOKEN, 
            config.CHANNEL_B_CHAT_ID, 
            bot_uname, 
            old_pack["file_id"], 
            rebranded_name, 
            invoice_desc, 
            old_pack["stars_price"], 
            thread_id=thread_id
        )
        
        notifier.send_log(f"Published Vault/Throwback Release: {rebranded_name} (YouTube ID: {vid_id})")
    except Exception as e:
        notifier.send_error(e, "run_throwback_release")
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def run_pipeline():
    """Main pipeline routine."""
    # First, scrape Reddit for any new posts
    scrape_reddit_links()
    
    queue = load_queue()
    if not queue:
        # If queue is empty, trigger Vault/Throwback Release
        run_throwback_release()
        return

    tried_urls = set()
    item = None
    url = ""
    title = ""
    reddit_id = ""
    description = ""
    size = 0
    ltype = ""
    
    while True:
        candidates = [q for q in queue if q["url"] not in tried_urls]
        if not candidates:
            print("All links in queue were checked and were either invalid or quota-exceeded.")
            run_throwback_release()
            return
            
        item = random.choice(candidates)
        url = item["url"]
        title = item["title"]
        reddit_id = item["reddit_id"]
        description = item["description"]
        tried_urls.add(url)
        
        print(f"Selected link to process: {url} (Title: {title})")
        
        # Verify link access & size
        is_valid, ltype, size = downloader.check_link(url)
        
        if not is_valid:
            print("Link is dead or invalid. Removing from queue.")
            queue.remove(item)
            save_queue(queue)
            save_processed_link(reddit_id)  # Mark processed so we don't scrape it again
            continue
            
        if ltype == "gdrive_quota":
            print("Google Drive quota exceeded. Re-queueing link to back and picking another.")
            queue.remove(item)
            queue.append(item)
            save_queue(queue)
            continue
            
        break

    # Proceed with download and processing
    temp_dir = os.path.join(config.BASE_DIR, "temp_pipeline")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        download_zip = os.path.join(temp_dir, "download.zip")
        extracted_dir = os.path.join(temp_dir, "extracted")
        cover_path = os.path.join(temp_dir, "cover.png")
        mockup_path = os.path.join(temp_dir, "mockup.png")
        overlay_path = os.path.join(temp_dir, "overlay.png")
        audio_path = os.path.join(temp_dir, "preview.mp3")
        srt_path = os.path.join(temp_dir, "subtitles.srt")
        video_path = os.path.join(temp_dir, "video.mp4")
        shorts_path = os.path.join(temp_dir, "shorts.mp4")
        
        # 1. Download ZIP
        success = downloader.download_file(url, download_zip)
        if not success:
            raise ValueError(f"Failed to download file from link: {url}")
            
        # 2. Extract & Rebrand
        audio_processor.unzip_pack(download_zip, extracted_dir)
        cats, all_files = audio_processor.process_and_rename_kit(extracted_dir)
        
        # Query OpenRouter for Rebranding Name and Genre
        try:
            rebranded_name, genre = query_deepseek_rebrand(title, description)
            rebranded_name = f"Arqive {rebranded_name}"
            print(f"DeepSeek Rebrand Successful: Name: '{rebranded_name}', Genre: '{genre}'")
        except Exception as e:
            print(f"DeepSeek rebrand failed: {e}. Using local fallback.")
            rebranded_name, genre = get_fallback_rebrand(title)
            rebranded_name = f"Arqive {rebranded_name}"
            notifier.send_telegram_message(f"⚠️ **DeepSeek Rebrand API Failed**: Used local fallback '{rebranded_name}' for pack.")
            
        # Generate cover and mockup art
        cover_generator.generate_cover_art(rebranded_name, genre, cover_path)
        mockup_generator.generate_3d_mockup(cover_path, mockup_path, rebranded_name, genre)
        
        # 3. Create Audio Showcase
        showcase = audio_processor.select_preview_showcase(cats)
        voice_tag = os.path.join(config.ASSETS_DIR, "voice_tag.wav")
        video_generator.compile_preview_audio(showcase, audio_path, voice_tag)
        
        # Create SRT Subtitles file and markers list
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
        
        # 4. Generate Video Visuals Tracklist Overlay (using dict markers)
        video_generator.create_tracklist_overlay(rebranded_name, genre, markers, overlay_path)
        
        # Compile video files
        video_generator.compile_video_16_9(audio_path, mockup_path, overlay_path, video_path, genre, markers, srt_path)
        video_generator.compile_video_9_16_shorts(audio_path, mockup_path, shorts_path, genre, rebranded_name)
        
        # 5. Package rebranded drumkit ZIP
        zip_base_name = os.path.join(temp_dir, clean_filename_for_zip(rebranded_name))
        zip_files = audio_processor.zip_pack(extracted_dir, zip_base_name)
        
        # 6. Upload rebranded files to Telegram using local Bot API (supports up to 2GB)
        # We upload all volumes and store their file_ids
        file_ids = []
        for zf in zip_files:
            fid = telegram_publisher.upload_document_local(config.TELEGRAM_BOT_TOKEN, config.CHANNEL_A_CHAT_ID, zf)
            if not fid:
                raise ValueError(f"Failed to upload zip part {zf} to Telegram.")
            file_ids.append(fid)
            
        # Determine pricing bracket based on total size
        total_size_mb = size / 1024 / 1024 if size > 0 else os.path.getsize(download_zip) / 1024 / 1024
        stars_price = 500  # default
        for bracket in config.PRICE_BRACKETS:
            if total_size_mb <= bracket["max_size_mb"]:
                stars_price = bracket["price"]
                break
                
        # 7. Publish Telegram storefront Invoice (Channel B) & Download (Channel A)
        bot_uname = telegram_publisher.get_bot_username(config.TELEGRAM_BOT_TOKEN)
        topic_a = config.GENRE_TOPICS_A.get(genre, config.GENRE_TOPICS_A["Default"])
        topic_b = config.GENRE_TOPICS_B.get(genre, config.GENRE_TOPICS_B["Default"])
        
        # Check if today is the Free Day (Promo Day)
        today_name = datetime.datetime.utcnow().strftime("%A")
        is_free_day = (today_name.lower() == config.FREE_DAY.lower())
        
        tg_invoice_link = ""
        tg_subscription_link = f"https://t.me/{bot_uname}"
        
        # Build description contents text
        contents_summary = []
        for cat, files in cats.items():
            if files:
                contents_summary.append(f"• {cat}: {len(files)} files")
        contents_text = "\n".join(contents_summary)
        
        if is_free_day:
            print("Today is Free Campaign Day! Publishing raw ZIP directly to Channel B.")
            free_caption = f"🎁 [FREE UNLOCKED] {rebranded_name}\n\n📂 CONTENTS:\n{contents_text}\n\nEnjoy this 100% free pack! No Stars or subscriptions required today!"
            # On Free days, we post the raw ZIP file directly to Channel B so anyone can click and download
            for fid in file_ids:
                telegram_publisher.publish_free_doc(config.TELEGRAM_BOT_TOKEN, config.CHANNEL_B_CHAT_ID, fid, free_caption, thread_id=topic_b)
            tg_invoice_link = f"https://t.me/c/{str(config.CHANNEL_B_CHAT_ID).replace('-100', '')}/{topic_b}"
        else:
            # Standard paid day: Post Invoice on Channel B, post raw ZIP on Channel A
            invoice_desc = f"💳 NEW RELEASE: {rebranded_name}\n\n📂 CONTENTS:\n{contents_text}\n\nDownload immediately by paying Stars below, or subscribe to our Premium Channel for free access!"
            
            # Post raw ZIP on private Channel A for premium members
            for fid in file_ids:
                telegram_publisher.publish_free_doc(config.TELEGRAM_BOT_TOKEN, config.CHANNEL_A_CHAT_ID, fid, f"📦 PREMIUM RELEASE: {rebranded_name}\n\n{contents_text}", thread_id=None)
                
            # Post invoice on Channel B
            # If multiple parts, we post the first part and link the others
            invoice_msg_id = telegram_publisher.publish_invoice(
                config.TELEGRAM_BOT_TOKEN, 
                config.CHANNEL_B_CHAT_ID, 
                bot_uname, 
                file_ids[0], 
                rebranded_name, 
                invoice_desc, 
                stars_price, 
                thread_id=topic_b
            )
            if invoice_msg_id:
                # Link format to invoice post
                tg_invoice_link = f"https://t.me/c/{str(config.CHANNEL_B_CHAT_ID).replace('-100', '')}/{invoice_msg_id}"

        # 8. Upload to YouTube
        yt_token = youtube_uploader.get_access_token()
        yt_tags = youtube_uploader.generate_tags_with_deepseek(rebranded_name, genre)
        
        yt_title = f"{rebranded_name} - {genre} Drum Kit Showcase [FREE]"
        if is_free_day:
            yt_title = f"[100% UNLOCKED] {rebranded_name} - {genre} Drum Kit [FREE DOWNLOAD]"
            
        desc = config.STATIC_DESC_TEMPLATE.format(
            pack_name=rebranded_name,
            tg_invoice_link=tg_invoice_link if tg_invoice_link else f"https://t.me/{bot_uname}",
            tg_subscription_link=tg_subscription_link,
            pack_contents=contents_text,
            affiliate_recommendations=config.AFFILIATE_LINKS.get(genre, "")
        )
        
        # Upload main video and Shorts
        yt_video_id = youtube_uploader.upload_video(video_path, yt_title, desc, yt_tags, yt_token)
        youtube_uploader.upload_video(shorts_path, f"{rebranded_name} #shorts #{genre.lower()}", desc, [genre.lower(), "shorts"], yt_token)
        
        # Pin top comment on main video
        comment_text = f"📥 Direct Download Link (No payment on Free Friday / Checkout Invoice): {tg_invoice_link if tg_invoice_link else tg_subscription_link}"
        youtube_uploader.add_comment_to_video(yt_video_id, comment_text, yt_token)

        # 9. Log success and save to registry
        packs = load_packs()
        packs.append({
            "reddit_id": reddit_id,
            "name": rebranded_name,
            "genre": genre,
            "file_id": file_ids[0],
            "file_ids": file_ids,
            "stars_price": stars_price,
            "youtube_id": yt_video_id,
            "tg_invoice_link": tg_invoice_link,
            "rating": 0.0,
            "ratings_count": 0,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "markers": [{"name": m["name"], "category": m["category"], "start": m["start"], "end": m["end"]} for m in markers]
        })
        save_packs(packs)
        
        # Remove from scraped queue and save links registry
        queue.remove(item)
        save_queue(queue)
        save_processed_link(reddit_id)
        
        notifier.send_log(
            f"Successfully processed & uploaded: **{rebranded_name}** ({genre})\n"
            f"YouTube ID: {yt_video_id}\n"
            f"Telegram Store Post: {tg_invoice_link if tg_invoice_link else 'Raw ZIP posted (Free Day)'}"
        )
        
        # Git commit and sync updates
        commit_git_changes(f"Auto-commit: Published {rebranded_name}")
        
    except Exception as e:
        notifier.send_error(e, f"process_link: {url}")
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def clean_filename_for_zip(name: str) -> str:
    """Gets a clean filename for zipping."""
    cleaned = name.replace(" ", "_").replace("[", "").replace("]", "")
    return re.sub(r'[^a-zA-Z0-9_-]', '', cleaned)

if __name__ == "__main__":
    run_pipeline()

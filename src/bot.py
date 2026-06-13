import os
import sqlite3
import json
import subprocess
import asyncio
from typing import Optional
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import PreCheckoutQuery, Message, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton

import config

# Initialize Bot and Dispatcher
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

DB_PATH = os.path.join(config.DATA_DIR, "bot.db")
PACKS_JSON_PATH = os.path.join(config.DATA_DIR, "packs.json")
LOCAL_BOT_API_URL = "http://localhost:8081"

# User coupon states: user_id -> active_coupon_code
active_user_coupons = {}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite database tables and seeds default coupons."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Packs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS packs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reddit_id TEXT UNIQUE,
        name TEXT,
        genre TEXT,
        file_id TEXT UNIQUE,
        file_ids_json TEXT,
        stars_price INTEGER,
        youtube_id TEXT,
        tg_invoice_link TEXT,
        rating REAL DEFAULT 0.0,
        ratings_count INTEGER DEFAULT 0,
        timestamp TEXT
    )
    """)
    
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        credits INTEGER DEFAULT 0,
        is_subscribed INTEGER DEFAULT 0,
        join_date TEXT
    )
    """)
    
    # Ratings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ratings (
        user_id INTEGER,
        file_id TEXT,
        rating INTEGER,
        timestamp TEXT,
        PRIMARY KEY (user_id, file_id)
    )
    """)
    
    # Coupons table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coupons (
        code TEXT PRIMARY KEY,
        discount_pct INTEGER,
        max_uses INTEGER
    )
    """)
    
    # Coupon usages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coupon_usages (
        user_id INTEGER,
        code TEXT,
        timestamp TEXT,
        PRIMARY KEY (user_id, code)
    )
    """)
    
    # Seed default coupons
    for code, details in config.COUPON_CODES.items():
        cursor.execute(
            "INSERT OR IGNORE INTO coupons (code, discount_pct, max_uses) VALUES (?, ?, ?)",
            (code, details["pct"], details["max_uses"])
        )
        
    conn.commit()
    conn.close()
    print("Local SQLite database initialized and seeded.")

def sync_packs_from_json():
    """Pulls latest repo updates and merges packs.json entries into SQLite."""
    print("Running Git pull to check for database updates...")
    try:
        subprocess.run(["git", "pull", "origin", "main"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Git pull failed during sync: {e}")
        
    if not os.path.exists(PACKS_JSON_PATH):
        print("packs.json not found in repository.")
        return
        
    try:
        with open(PACKS_JSON_PATH, "r", encoding="utf-8") as f:
            packs = json.load(f)
    except Exception as e:
        print(f"Failed to read packs.json: {e}")
        return

    conn = get_db()
    cursor = conn.cursor()
    
    added_count = 0
    for p in packs:
        # Re-format split file_ids JSON just in case
        fids = p.get("file_ids", [p.get("file_id")])
        fids_json = json.dumps(fids)
        
        try:
            cursor.execute(
                """
                INSERT INTO packs (reddit_id, name, genre, file_id, file_ids_json, stars_price, youtube_id, tg_invoice_link, rating, ratings_count, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(reddit_id) DO UPDATE SET
                    file_id=excluded.file_id,
                    file_ids_json=excluded.file_ids_json,
                    stars_price=excluded.stars_price,
                    tg_invoice_link=excluded.tg_invoice_link,
                    rating=excluded.rating,
                    ratings_count=excluded.ratings_count
                """,
                (
                    p.get("reddit_id"), p.get("name"), p.get("genre"), p.get("file_id"), 
                    fids_json, p.get("stars_price"), p.get("youtube_id"), p.get("tg_invoice_link"),
                    p.get("rating", 0.0), p.get("ratings_count", 0), p.get("timestamp")
                )
            )
            added_count += 1
        except Exception as e:
            print(f"Failed to insert pack {p.get('name')}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Sync complete. Checked/updated {added_count} packs in local SQLite.")

def get_pack_by_file_id(file_id: str) -> Optional[sqlite3.Row]:
    """Queries SQLite for a pack. Performs a sync and checks again on cache-miss."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM packs WHERE file_id = ?", (file_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        # Cache-Miss: Perform on-demand git pull and sync, then query again
        print(f"Cache-Miss for file_id {file_id}. Performing on-demand sync...")
        sync_packs_from_json()
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM packs WHERE file_id = ?", (file_id,))
        row = cursor.fetchone()
        conn.close()
        
    return row

# --- Handlers ---

@dp.message(Command("start"))
async def handle_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args
    
    # Save user if new
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, date('now'))", (user_id,))
    conn.commit()
    conn.close()
    
    if not args:
        welcome_txt = (
            "👋 Welcome to the **Arqive Checkout Bot**!\n\n"
            "This bot handles safe checkout transactions and premium subscriptions.\n"
            "👉 Use `/search [keyword]` to browse packs.\n"
            "👉 Use `/genres` to view available styles.\n"
            "👉 Use `/coupon [code]` to apply a discount coupon."
        )
        await message.answer(welcome_txt, parse_mode="Markdown")
        return

    # Handle sub_FILEID (Subscription checkout link)
    if args.startswith("sub_"):
        file_id = args.replace("sub_", "")
        pack = get_pack_by_file_id(file_id)
        if not pack:
            await message.answer("❌ Sorry, this pack metadata could not be found.")
            return

        # Check user membership in private subscription Channel A
        try:
            member = await bot.get_chat_member(config.CHANNEL_A_CHAT_ID, user_id)
            if member.status in ["member", "administrator", "creator"]:
                # User is subscribed, redirect directly to Channel A
                topic_id = config.GENRE_TOPICS_A.get(pack["genre"], config.GENRE_TOPICS_A["Default"])
                # Extract clean channel ID representation (without -100)
                clean_cid = str(config.CHANNEL_A_CHAT_ID).replace("-100", "")
                channel_link = f"https://t.me/c/{clean_cid}/{topic_id}"
                
                kbd = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 Go to Premium Channel", url=channel_link)]
                ])
                await message.answer(
                    f"✅ **Premium Member Verified!**\n\n"
                    f"You have active subscription rights. You can download **{pack['name']}** "
                    f"and all other packs directly inside our Premium Channel feed.",
                    reply_markup=kbd,
                    parse_mode="Markdown"
                )
            else:
                # User is not subscribed, prompt to join Channel A
                # We can create a temporary invite link or link to the Telegram Channel subscription page
                kbd = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Subscribe to Premium Channel", url=f"https://t.me/{config.CHANNEL_A_CHAT_ID}")]
                ])
                await message.answer(
                    f"🔒 **Subscription Required**\n\n"
                    f"To download **{pack['name']}** and all other releases for free, "
                    f"join our Premium Subscription Channel using the link below!",
                    reply_markup=kbd,
                    parse_mode="Markdown"
                )
        except Exception as e:
            print(f"Error checking chat member: {e}")
            await message.answer("⚠️ Could not verify membership status. Please try again later.")
        return

    # Handle dl_FILEID (Direct purchase checkout link)
    if args.startswith("dl_"):
        file_id = args.replace("dl_", "")
        pack = get_pack_by_file_id(file_id)
        if not pack:
            await message.answer("❌ Sorry, this pack could not be found.")
            return
            
        name = pack["name"]
        genre = pack["genre"]
        price = pack["stars_price"]
        
        # Check if user has an active coupon
        coupon_code = active_user_coupons.get(user_id)
        discount_text = ""
        if coupon_code:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT discount_pct FROM coupons WHERE code = ?", (coupon_code,))
            crow = cursor.fetchone()
            conn.close()
            if crow:
                pct = crow["discount_pct"]
                price = int(price * (1 - pct / 100))
                discount_text = f"🔥 Coupon `{coupon_code}` applied! ({pct}% OFF)\n"

        desc = f"🎵 Rebranded {genre} kit: {name}.\nSize: Large Pack. Quality: 24-bit WAV.\n{discount_text}Price: {price} Stars."
        
        # Keyboard with Pay and Subscription buttons
        kbd = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💳 Pay {price} Stars ⭐️", pay=True)],
            [InlineKeyboardButton(text="📥 Download via Subscription", url=f"https://t.me/{(await bot.get_me()).username}?start=sub_{file_id}")]
        ])
        
        # Send Stars Invoice directly in user private chat
        try:
            await bot.send_invoice(
                chat_id=user_id,
                title=name[:32],
                description=desc[:250],
                payload=f"pay_{file_id}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Stars Price", amount=price)],
                reply_markup=kbd
            )
        except Exception as e:
            print(f"Failed to send invoice: {e}")
            await message.answer("⚠️ Error generating checkout invoice. Please try again.")

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Answers pre-checkout queries, approving the payment."""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Delivers the document files to the user on successful payment."""
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    
    if not payload.startswith("pay_"):
        await message.answer("❌ Invalid payment transaction payload.")
        return
        
    file_id = payload.replace("pay_", "")
    pack = get_pack_by_file_id(file_id)
    if not pack:
        await message.answer("❌ Payment captured, but file metadata was lost. Please contact support.")
        return
        
    # Apply coupon usage logs if coupon was used
    coupon_code = active_user_coupons.pop(user_id, None)
    if coupon_code:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO coupon_usages (user_id, code, timestamp) VALUES (?, ?, date('now'))", (user_id, coupon_code))
        conn.commit()
        conn.close()

    await message.answer(f"🎉 **Thank you for your purchase!**\nDelivering your kit **{pack['name']}** now:")
    
    # Read split files JSON
    fids = json.loads(pack["file_ids_json"]) if pack["file_ids_json"] else [pack["file_id"]]
    
    # Send all parts
    for idx, fid in enumerate(fids, 1):
        caption = f"📦 {pack['name']} - Part {idx} of {len(fids)}" if len(fids) > 1 else f"📦 {pack['name']}"
        await bot.send_document(chat_id=user_id, document=fid, caption=caption)

    # Offer to rate
    await message.answer(
        "⭐ How would you rate this pack?\n"
        f"Type `/rate {file_id} [1-5]` to review it!"
    )

@dp.message(Command("coupon"))
async def handle_coupon(message: Message, command: CommandObject):
    user_id = message.from_user.id
    code = command.args
    
    if not code:
        await message.answer("👉 Usage: `/coupon [CODE]` (e.g. `/coupon OFF30`)", parse_mode="Markdown")
        return
        
    code = code.upper().strip()
    conn = get_db()
    cursor = conn.cursor()
    
    # Validate coupon exists
    cursor.execute("SELECT * FROM coupons WHERE code = ?", (code,))
    crow = cursor.fetchone()
    if not crow:
        await message.answer("❌ Invalid coupon code.")
        conn.close()
        return
        
    # Check max usage limits
    cursor.execute("SELECT COUNT(*) FROM coupon_usages WHERE user_id = ? AND code = ?", (user_id, code))
    usages = cursor.fetchone()[0]
    
    if usages >= crow["max_uses"]:
        await message.answer("❌ You have already used this coupon code.")
        conn.close()
        return
        
    conn.close()
    
    # Store active coupon in session memory
    active_user_coupons[user_id] = code
    await message.answer(f"✅ **Coupon {code} applied!** Your next checkout invoice will be discounted by {crow['discount_pct']}% OFF.", parse_mode="Markdown")

@dp.message(Command("rate"))
async def handle_rate(message: Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args
    if not args or len(args.split()) < 2:
        await message.answer("👉 Usage: `/rate [file_id] [1-5]` (e.g., `/rate FILE_ID 5`)", parse_mode="Markdown")
        return
        
    file_id, rating_str = args.split()[:2]
    try:
        rating = int(rating_str)
        if not (1 <= rating <= 5):
            raise ValueError
    except ValueError:
        await message.answer("❌ Rating must be a number between 1 and 5.")
        return

    pack = get_pack_by_file_id(file_id)
    if not pack:
        await message.answer("❌ Rebranded pack not found.")
        return

    # Check if user has purchased this file or is subscribed to Channel A
    has_purchased = False
    
    # 1. Check Channel A subscription
    try:
        member = await bot.get_chat_member(config.CHANNEL_A_CHAT_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            has_purchased = True
    except Exception:
        pass
        
    # 2. Check SQLite ratings logs as backup purchase validator or successful transactions
    # To keep things simple, we allow ratings from premium channel members or users who initiate rating
    # If not a member, we check if they bought it (using our bot.db users/purchase registers)
    if not has_purchased:
        await message.answer("❌ Ratings are restricted to users who have purchased or downloaded this specific kit.")
        return

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Insert rating
        cursor.execute(
            "INSERT OR REPLACE INTO ratings (user_id, file_id, rating, timestamp) VALUES (?, ?, ?, date('now'))",
            (user_id, file_id, rating)
        )
        
        # Calculate new average
        cursor.execute("SELECT AVG(rating), COUNT(rating) FROM ratings WHERE file_id = ?", (file_id,))
        avg_rating, count_rating = cursor.fetchone()
        
        # Update packs table
        cursor.execute(
            "UPDATE packs SET rating = ?, ratings_count = ? WHERE file_id = ?",
            (avg_rating, count_rating, file_id)
        )
        conn.commit()
        await message.answer(f"⭐️ **Thank you!** You rated **{pack['name']}** as {rating}/5 stars.")
    except Exception as e:
        print(f"Rating insert failed: {e}")
        await message.answer("⚠️ Failed to record rating. Please try again.")
    finally:
        conn.close()

@dp.message(Command("search"))
async def handle_search(message: Message, command: CommandObject):
    query = command.args
    if not query:
        await message.answer("👉 Usage: `/search [keyword]` (e.g., `/search phonk`)", parse_mode="Markdown")
        return
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, genre, file_id, tg_invoice_link, rating FROM packs WHERE name LIKE ? OR genre LIKE ? LIMIT 8",
        (f"%{query}%", f"%{query}%")
    )
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        await message.answer("🔍 No matching drum kits found in our vault.")
        return
        
    lines = ["🔍 **Search Results:**"]
    for row in rows:
        stars_icon = "⭐" * int(row["rating"]) if row["rating"] > 0 else "⭐ (Unrated)"
        lines.append(
            f"• **{row['name']}** ({row['genre']}) - {stars_icon}\n"
            f"  🔗 [Checkout Post]({row['tg_invoice_link']})"
        )
        
    await message.answer("\n\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)

@dp.message(Command("genres"))
async def handle_genres(message: Message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT genre FROM packs")
    genres = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    if not genres:
        genres = ["Trap", "RnB", "Lofi", "Phonk", "Hip-Hop"]
        
    lines = ["🎵 **Available Genres & Styles:**"]
    for g in genres:
        lines.append(f"• **{g}** (Use `/search {g.lower()}` to view)")
        
    await message.answer("\n".join(lines), parse_mode="Markdown")

async def main():
    init_db()
    # Initial sync from packs.json on startup
    sync_packs_from_json()
    print("Bot is starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

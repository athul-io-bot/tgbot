import os
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from utils import encode_series_name, decode_series_name
import files
import episodes
import database
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPONSOR_CHANNEL = os.getenv("SPONSOR_CHANNEL")
DATABASE_CHANNEL = os.getenv("DATABASE_CHANNEL")
ADMINS = list(map(int, os.getenv("ADMINS").split(",")))

app = Client("tv_series_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database setup
conn = sqlite3.connect("files.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_name TEXT,
    resolution TEXT,
    file_id TEXT,
    caption TEXT
)
""")
conn.commit()

# Command to add file (for admin use only)
@app.on_message(filters.command("addfile") & filters.private)
async def add_file(client, message):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ You are not authorized.")
        return

    try:
        text = message.text.split(" ", 1)[1]
        parts = text.split(";")
        if len(parts) < 2:
            await message.reply("Use format: Series Name;resolution;caption")
            return
        series_name = parts[0].strip()
        resolution = parts[1].strip()
        caption = parts[2].strip() if len(parts) > 2 else ""

        if not message.document:
            await message.reply("Please attach a file.")
            return

        forwarded = await message.forward(DATABASE_CHANNEL)
        file_id = forwarded.document.file_id

        cursor.execute("INSERT INTO files (series_name, resolution, file_id, caption) VALUES (?, ?, ?, ?)",
                       (series_name, resolution, file_id, caption))
        conn.commit()

        await message.reply("✅ File saved successfully!")

    except Exception as e:
        await message.reply(f"⚠ Error: {e}")

# Handler to send a series message in main channel (admin use only)
@app.on_message(filters.command("sendseries") & filters.private)
async def send_series(client, message):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ You are not authorized.")
        return

    try:
        text = message.text.split(" ", 1)[1]
        series_name = text.strip()
        encoded_name = encode_series_name(series_name)

        await app.send_message(
            chat_id="@YourMainChannel",
            text=f"{series_name} – Episode List",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Download", callback_data=f"series_{encoded_name}")]
            ])
        )
        await message.reply("✅ Series message sent!")

    except Exception as e:
        await message.reply(f"⚠ Error: {e}")

# Series selected by user
@app.on_callback_query(filters.regex(r"series_(.+)"))
async def series_selected(client, callback_query):
    encoded_name = callback_query.data.split("_", 1)[1]
    series_name = decode_series_name(encoded_name)
    user_id = callback_query.from_user.id

    await client.send_message(
        chat_id=user_id,
        text=f"You selected *{series_name}*. Please join the channel first.",
        parse_mode="markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Channel 🔊", url=f"https://t.me/{SPONSOR_CHANNEL[1:]}")],
            [InlineKeyboardButton("Check Subscription ✅", callback_data=f"check_sub_{encoded_name}")]
        ])
    )
    await callback_query.answer()

# Subscription check handler
@app.on_callback_query(filters.regex(r"check_sub_(.+)"))
async def check_subscription(client, callback_query):
    encoded_name = callback_query.data.split("_", 1)[1]
    series_name = decode_series_name(encoded_name)
    user_id = callback_query.from_user.id

    try:
        member = await client.get_chat_member(SPONSOR_CHANNEL, user_id)
        if member.status not in ["left", "kicked"]:
            await callback_query.message.edit(
                f"Thanks for joining! Choose a resolution for *{series_name}*:",
                parse_mode="markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("480p", callback_data=f"res_{encoded_name}_480")],
                    [InlineKeyboardButton("720p", callback_data=f"res_{encoded_name}_720")],
                    [InlineKeyboardButton("1080p", callback_data=f"res_{encoded_name}_1080")]
                ])
            )
        else:
            await callback_query.answer("You must join the channel first!", show_alert=True)
    except Exception:
        await callback_query.answer("Unable to verify subscription.", show_alert=True)

# Resolution selected handler
@app.on_callback_query(filters.regex(r"res_(.+)_(\d+)"))
async def resolution_selected(client, callback_query):
    parts = callback_query.data.split("_")
    encoded_name = parts[1]
    resolution = parts[2]
    series_name = decode_series_name(encoded_name)

    cursor.execute("SELECT file_id, caption FROM files WHERE series_name=? AND resolution=?", (series_name, resolution))
    files = cursor.fetchall()

    if files:
        await callback_query.message.edit(f"Sending files for {series_name} ({resolution}p)...")
        for file_id, caption in files:
            await client.send_document(chat_id=callback_query.from_user.id, document=file_id, caption=caption or "")
    else:
        await callback_query.answer("No files found for this resolution.", show_alert=True)

if __name__ == "__main__":
    print("Bot is running...")
    app.run()

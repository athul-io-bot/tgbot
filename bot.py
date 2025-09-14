import os
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPONSOR_CHANNEL = os.getenv("SPONSOR_CHANNEL")      # e.g., @sponsor_channel
DATABASE_CHANNEL = os.getenv("DATABASE_CHANNEL")    # e.g., @database_channel
ADMINS = list(map(int, os.getenv("ADMINS").split(",")))

app = Client("tv_series_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database connection
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

@app.on_message(filters.command("addfile") & filters.private)
async def add_file(client, message):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ You are not authorized to use this command.")
        return
    
    # Proceed with file handling
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

# Example handler for user clicking the initial button in your main channel
@app.on_callback_query(filters.regex("start_dm"))
async def handle_start(client, callback_query):
    user_id = callback_query.from_user.id
    await client.send_message(
        chat_id=user_id,
        text="Welcome! Please join our sponsor channel first.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Sponsor Channel", url=f"https://t.me/{SPONSOR_CHANNEL[1:]}")],
            [InlineKeyboardButton("Check Subscription ✅", callback_data="check_sub")]
        ])
    )

# Check subscription
@app.on_callback_query(filters.regex("check_sub"))
async def check_subscription(client, callback_query):
    user_id = callback_query.from_user.id
    try:
        member = await client.get_chat_member(SPONSOR_CHANNEL, user_id)
        if member.status not in ["left", "kicked"]:
            await callback_query.message.edit(
                "Thanks for joining! Please select a TV series:",
                reply_markup=generate_series_buttons()
            )
        else:
            await callback_query.answer("You must join the sponsor channel first!", show_alert=True)
    except Exception as e:
        await callback_query.answer("Unable to verify subscription.", show_alert=True)

# Generate series buttons dynamically
def generate_series_buttons():
    cursor.execute("SELECT DISTINCT series_name FROM files")
    series_list = cursor.fetchall()
    buttons = []
    for series in series_list:
        name = series[0]
        buttons.append([InlineKeyboardButton(name, callback_data=f"series_{name}")])
    return InlineKeyboardMarkup(buttons)

# Series selected → show resolutions
@app.on_callback_query(filters.regex(r"series_(.+)"))
async def series_selected(client, callback_query):
    series_name = callback_query.data.split("_", 1)[1]
    callback_query.message.edit(
        f"You selected: {series_name}\nChoose a resolution:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("480p", callback_data=f"res_{series_name}_480")],
            [InlineKeyboardButton("720p", callback_data=f"res_{series_name}_720")],
            [InlineKeyboardButton("1080p", callback_data=f"res_{series_name}_1080")]
        ])
    )

# Resolution selected → send files
@app.on_callback_query(filters.regex(r"res_(.+)_(\d+)"))
async def resolution_selected(client, callback_query):
    series_name = callback_query.data.split("_")[1]
    resolution = callback_query.data.split("_")[2]

    cursor.execute("SELECT file_id, caption FROM files WHERE series_name=? AND resolution=?", (series_name, resolution))
    files = cursor.fetchall()

    if files:
        await callback_query.message.edit(f"Sending files for {series_name} ({resolution}p)...")
        for f in files:
            await client.send_document(
                chat_id=callback_query.from_user.id,
                document=f[0],
                caption=f[1] or ""
            )
    else:
        await callback_query.answer("No files found for this resolution.", show_alert=True)

# Start command
@app.on_message(filters.command("start") & filters.private)
async def start_message(client, message):
    await message.reply(
        "Welcome! Click below to get started.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Get TV Series", callback_data="start_dm")]
        ])
    )

if __name__ == "__main__":
    print("Bot is running...")
    app.run()

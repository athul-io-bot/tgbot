from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main import app
from utils import decode_series_name
from database import cursor

# List episodes with pagination
@app.on_callback_query(filters.regex(r"list_series_(.+)_(\d+)"))
async def list_series(client, callback_query):
    encoded_name = callback_query.data.split("_")[2]
    page = int(callback_query.data.split("_")[3])
    series_name = decode_series_name(encoded_name)

    cursor.execute("SELECT file_id, caption FROM files WHERE series_name=?", (series_name,))
    files = cursor.fetchall()

    if not files:
        await callback_query.answer("No episodes available.", show_alert=True)
        return

    per_page = 5
    start = page * per_page
    end = start + per_page
    page_files = files[start:end]

    buttons = [[InlineKeyboardButton(caption or "Episode", callback_data=f"file_{file_id}")] for file_id, caption in page_files]

    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list_series_{encoded_name}_{page-1}"))
    if end < len(files):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"list_series_{encoded_name}_{page+1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    await callback_query.message.edit(f"Episodes for *{series_name}*:", parse_mode="markdown", reply_markup=InlineKeyboardMarkup(buttons))


# Send selected episode
@app.on_callback_query(filters.regex(r"file_(.+)"))
async def send_episode(client, callback_query):
    file_id = callback_query.data.split("_")[1]

    cursor.execute("SELECT caption FROM files WHERE file_id=?", (file_id,))
    row = cursor.fetchone()

    if row:
        caption = row[0] or "Episode"
        await client.send_document(chat_id=callback_query.from_user.id, document=file_id, caption=caption)
        await callback_query.answer("Sending episode...")
    else:
        await callback_query.answer("File not found.", show_alert=True)

from pyrogram import filters
from pyrogram.types import Message
from main import app, ADMINS, SPONSOR_CHANNEL
from database import cursor, conn
import datetime

@app.on_message(filters.command("addfile") & filters.private)
async def add_file(client, message: Message):
    if message.from_user.id not in ADMINS:
        await message.reply("❌ You are not authorized.")
        return

    replied = message.reply_to_message

    if not replied:
        await message.reply("📂 Please reply to a file message.")
        return

    # Parse command arguments: /addfile <Series Name>|<Resolution>
    try:
        text = message.text.split(" ", 1)[1].strip()
        series_name, resolution = text.split("|")
    except:
        await message.reply("Usage: /addfile <Series Name>|<Resolution>")
        return

    file_id = None
    caption = None

    # Case 1: Normal file (document, video, audio, animation)
    if replied.document:
        file_id = replied.document.file_id
        caption = replied.caption or replied.document.file_name
    elif replied.video:
        file_id = replied.video.file_id
        caption = replied.caption or "Video File"
    elif replied.audio:
        file_id = replied.audio.file_id
        caption = replied.caption or "Audio File"
    elif replied.animation:
        file_id = replied.animation.file_id
        caption = replied.caption or "Animation File"

    # Case 2: Forwarded file from another bot
    elif replied.forward_from_chat and replied.forward_from_chat.type == "bot":
        # Copy the message to your database channel
        copied = await client.copy_message(
            chat_id=SPONSOR_CHANNEL,
            from_chat_id=replied.chat.id,
            message_id=replied.message_id
        )
        # Determine type
        if copied.document:
            file_id = copied.document.file_id
            caption = copied.caption or copied.document.file_name
        elif copied.video:
            file_id = copied.video.file_id
            caption = copied.caption or "Video File"
        elif copied.audio:
            file_id = copied.audio.file_id
            caption = copied.caption or "Audio File"
        elif copied.animation:
            file_id = copied.animation.file_id
            caption = copied.caption or "Animation File"

    if not file_id:
        await message.reply("❌ Unable to process this file type.")
        return

    # Forward normal files to the database channel if not copied already
    if not (replied.forward_from_chat and replied.forward_from_chat.type == "bot"):
        db_msg = await client.send_document(
            chat_id=SPONSOR_CHANNEL,
            document=file_id,
            caption=f"{series_name}|{resolution}|{caption}"
        )
        file_id = db_msg.document.file_id  # use DB copy id

    # Save in database
    cursor.execute("""
        INSERT INTO files (series_name, resolution, file_id, caption, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (series_name.strip(), resolution.strip(), file_id, caption, datetime.datetime.now().isoformat()))
    conn.commit()

    await message.reply("✅ File added successfully!")

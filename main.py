import os
import asyncio
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]

MAX_SIZE = 45 * 1024 * 1024


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 My Leech Bot\n\n"
        "Commands:\n"
        "/start - Start bot\n"
        "/help - Help\n"
        "/leech URL - Download direct link\n\n"
        "Send /leech followed by a direct HTTP/HTTPS download link."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 Usage:\n"
        "/leech https://example.com/file.zip\n\n"
        "Only direct download links are supported.\n"
        "Maximum file size: approximately 45 MB."
    )


async def leech(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: /leech https://example.com/file.zip"
        )
        return

    url = context.args[0]
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        await update.message.reply_text("❌ Invalid download URL.")
        return

    status = await update.message.reply_text("⏳ Download starting...")

    try:
        with tempfile.TemporaryDirectory() as folder:
            filepath = Path(folder) / "download.bin"
            total = 0

            timeout = aiohttp.ClientTimeout(total=1800)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    url, allow_redirects=True
                ) as response:
                    response.raise_for_status()

                    length = response.content_length
                    if length is not None and length > MAX_SIZE:
                        await status.edit_text("❌ File exceeds the size limit.")
                        return

                    with filepath.open("wb") as file:
                        async for chunk in response.content.iter_chunked(256 * 1024):
                            total += len(chunk)

                            if total > MAX_SIZE:
                                await status.edit_text(
                                    "❌ File exceeds the size limit."
                                )
                                return

                            file.write(chunk)

            await status.edit_text("📤 Uploading to Telegram...")

            with filepath.open("rb") as file:
                await update.message.reply_document(
                    document=file,
                    filename="download.bin",
                    read_timeout=600,
                    write_timeout=600,
                    connect_timeout=60,
                )

            await status.delete()

    except Exception as error:
        print(f"Download error: {error}")
        await status.edit_text(
            "❌ Download failed. Check the link or try another direct link."
        )


async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("leech", leech))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

"""
Telegram PDF Bot - Main Entry Point
Handles PDF upload, processing, and delivery via Pyrogram
Supports files up to 300MB with optimized download/upload
"""

import os
import sys
import asyncio
import tempfile
import logging
from pathlib import Path
from datetime import datetime, timezone

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait

from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import PDF processor
from pdf_processor import compress_pdf, resize_to_a4, process_pdf, get_pdf_info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Telegram credentials from environment
API_ID = os.environ.get("TELEGRAM_API_ID")
API_HASH = os.environ.get("TELEGRAM_API_HASH")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Validate credentials
if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("Missing Telegram credentials! Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN")
    sys.exit(1)

# Create Pyrogram client
app = Client(
    "pdf_bot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir=str(ROOT_DIR)
)

# Store pending files waiting for user choice
# Format: {user_id: {file_id, original_name, file_size, message, resize_a4, waiting_filename}}
pending_files = {}

# Processing state to prevent double-processing
processing_files = set()

# Stats tracking
stats = {
    "total_processed": 0,
    "total_bytes_saved": 0,
    "start_time": datetime.now(timezone.utc)
}


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()


def get_processing_keyboard():
    """Create inline keyboard for processing options."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Compress Only", callback_data="compress_only"),
            InlineKeyboardButton("📐 Compress + A4", callback_data="compress_a4")
        ]
    ])


@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    """Handle /start command."""
    await message.reply_text(
        "**📄 PDF Optimizer Bot**\n\n"
        "Send me a PDF file and I'll help you:\n"
        "• **Compress** - Reduce file size\n"
        "• **Compress + A4** - Compress & resize to A4\n\n"
        "**How to use:**\n"
        "1. Send a PDF file\n"
        "2. Choose processing option\n"
        "3. Enter filename for output\n"
        "4. Get optimized PDF!\n\n"
        "Supports files up to 300MB."
    )


@app.on_message(filters.command("stats"))
async def stats_handler(client: Client, message: Message):
    """Handle /stats command."""
    uptime = datetime.now(timezone.utc) - stats["start_time"]
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    saved_mb = round(stats["total_bytes_saved"] / (1024 * 1024), 2)
    
    await message.reply_text(
        f"**📊 Bot Statistics**\n\n"
        f"📄 PDFs Processed: {stats['total_processed']}\n"
        f"💾 Total Space Saved: {saved_mb} MB\n"
        f"⏱️ Uptime: {hours}h {minutes}m {seconds}s"
    )


@app.on_message(filters.document)
async def document_handler(client: Client, message: Message):
    """Handle incoming PDF documents."""
    document = message.document
    
    # Check if it's a PDF
    if not document.file_name or not document.file_name.lower().endswith('.pdf'):
        if document.mime_type != "application/pdf":
            await message.reply_text("❌ Please send a PDF file.")
            return
    
    file_id = document.file_id
    file_size = document.file_size
    original_name = document.file_name or "document.pdf"
    
    # Check file size (300MB limit)
    max_size = 300 * 1024 * 1024  # 300MB in bytes
    if file_size > max_size:
        await message.reply_text(
            f"❌ File too large! Maximum size is 300MB.\n"
            f"Your file: {round(file_size / (1024 * 1024), 1)}MB"
        )
        return
    
    user_id = message.from_user.id
    
    # Store file info for later processing
    pending_files[user_id] = {
        "file_id": file_id,
        "original_name": original_name,
        "file_size": file_size,
        "message": message,
        "resize_a4": False,
        "waiting_filename": False
    }
    
    # Show options
    size_mb = round(file_size / (1024 * 1024), 2)
    
    await message.reply_text(
        f"**📄 {original_name}**\n"
        f"📦 Size: {size_mb} MB\n\n"
        f"Choose processing option:",
        reply_markup=get_processing_keyboard()
    )


@app.on_callback_query(filters.regex("^(compress_only|compress_a4)$"))
async def process_callback(client: Client, callback: CallbackQuery):
    """Handle processing option selection."""
    user_id = callback.from_user.id
    action = callback.data
    
    # Check if user has pending file
    if user_id not in pending_files:
        await callback.answer("❌ No file found. Please send a PDF first.", show_alert=True)
        return
    
    file_info = pending_files[user_id]
    
    # Store the choice and ask for filename
    file_info["resize_a4"] = (action == "compress_a4")
    file_info["waiting_filename"] = True
    pending_files[user_id] = file_info
    
    mode_text = "Compress + A4" if file_info["resize_a4"] else "Compress Only"
    
    await callback.message.edit_text(
        f"**📄 {file_info['original_name']}**\n"
        f"⚙️ Mode: {mode_text}\n\n"
        f"📝 **Enter the output filename:**\n"
        f"(without .pdf extension)\n\n"
        f"Or send /skip to use original name"
    )
    await callback.answer()


@app.on_message(filters.command("skip"))
async def skip_handler(client: Client, message: Message):
    """Handle /skip command - use original filename."""
    user_id = message.from_user.id
    
    if user_id not in pending_files:
        await message.reply_text("No file to process. Send a PDF first.")
        return
    
    file_info = pending_files[user_id]
    
    if not file_info.get("waiting_filename"):
        await message.reply_text("Please select a processing option first.")
        return
    
    # Use original name with optimized_ prefix
    original_name = file_info["original_name"]
    output_filename = f"optimized_{original_name}"
    
    # Process the file
    status_msg = await message.reply_text("⏳ Starting processing...")
    await process_file(client, status_msg, file_info, output_filename)
    
    # Cleanup
    if user_id in pending_files:
        del pending_files[user_id]


@app.on_message(filters.text & ~filters.command(["start", "stats", "skip"]))
async def text_handler(client: Client, message: Message):
    """Handle text messages (for filename input)."""
    user_id = message.from_user.id
    
    if user_id not in pending_files:
        return
    
    file_info = pending_files[user_id]
    
    if not file_info.get("waiting_filename"):
        return
    
    # Get filename from user input
    new_name = sanitize_filename(message.text.strip())
    if not new_name:
        await message.reply_text("❌ Invalid filename. Please try again.")
        return
    
    # Add .pdf extension if not present
    if not new_name.lower().endswith('.pdf'):
        new_name += '.pdf'
    
    # Process the file
    status_msg = await message.reply_text("⏳ Starting processing...")
    await process_file(client, status_msg, file_info, new_name)
    
    # Cleanup
    if user_id in pending_files:
        del pending_files[user_id]


async def process_file(client: Client, status_message: Message, file_info: dict, output_filename: str):
    """Process the PDF file."""
    file_id = file_info["file_id"]
    original_name = file_info["original_name"]
    file_size = file_info["file_size"]
    original_message = file_info["message"]
    resize_a4 = file_info["resize_a4"]
    
    # Prevent double-processing
    if file_id in processing_files:
        await status_message.edit_text("⚠️ This file is already being processed.")
        return
    
    processing_files.add(file_id)
    
    mode_text = "Compress + A4 Resize" if resize_a4 else "Compress Only"
    
    # Update status
    await status_message.edit_text(
        f"**⏳ Processing your PDF...**\n\n"
        f"📄 File: {original_name}\n"
        f"📦 Size: {round(file_size / (1024 * 1024), 2)} MB\n"
        f"📝 Output: {output_filename}\n"
        f"⚙️ Mode: {mode_text}\n\n"
        "⬇️ Downloading..."
    )
    
    input_path = None
    output_path = None
    
    try:
        start_time = datetime.now(timezone.utc)
        
        # Create temp files
        fd_in, input_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd_in)
        fd_out, output_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd_out)
        
        # Download file
        logger.info(f"Downloading: {original_name} ({file_size} bytes)")
        
        await client.download_media(
            original_message,
            file_name=input_path
        )
        
        download_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Download completed in {download_time:.1f}s")
        
        # Update status
        await status_message.edit_text(
            f"**⏳ Processing your PDF...**\n\n"
            f"📄 File: {original_name}\n"
            f"📦 Size: {round(file_size / (1024 * 1024), 2)} MB\n"
            f"📝 Output: {output_filename}\n"
            f"⚙️ Mode: {mode_text}\n\n"
            f"✅ Downloaded in {download_time:.1f}s\n"
            "🔄 Processing..."
        )
        
        # Get original PDF info
        original_info = get_pdf_info(input_path)
        
        # Process PDF
        process_start = datetime.now(timezone.utc)
        
        if resize_a4:
            # Full pipeline: compress + A4 resize
            success, error_msg = process_pdf(input_path, output_path)
        else:
            # Compress only
            success = compress_pdf(input_path, output_path)
            error_msg = "" if success else "Compression failed"
        
        process_time = (datetime.now(timezone.utc) - process_start).total_seconds()
        
        if not success:
            await status_message.edit_text(
                f"**❌ Processing failed**\n\n"
                f"Error: {error_msg}\n\n"
                "Please try again with a different file."
            )
            return
        
        # Get processed PDF info
        processed_info = get_pdf_info(output_path)
        
        logger.info(f"Processing completed in {process_time:.1f}s")
        
        # Update status
        await status_message.edit_text(
            f"**⏳ Processing your PDF...**\n\n"
            f"📄 File: {original_name}\n"
            f"📦 Size: {round(file_size / (1024 * 1024), 2)} MB\n"
            f"📝 Output: {output_filename}\n"
            f"⚙️ Mode: {mode_text}\n\n"
            f"✅ Downloaded in {download_time:.1f}s\n"
            f"✅ Processed in {process_time:.1f}s\n"
            "⬆️ Uploading result..."
        )
        
        # Upload processed file
        while True:
            try:
                await original_message.reply_document(
                    document=output_path,
                    file_name=output_filename,
                    caption=(
                        f"**✅ PDF Optimized!**\n\n"
                        f"📄 Original: {original_info['size_mb']} MB ({original_info['pages']} pages)\n"
                        f"📦 Processed: {processed_info['size_mb']} MB ({processed_info['pages']} pages)\n"
                        f"💾 Saved: {round(original_info['size_mb'] - processed_info['size_mb'], 2)} MB\n"
                        f"⚙️ Mode: {mode_text}"
                    )
                )
                break
            except FloodWait as e:
                logger.warning(f"FloodWait: sleeping {e.value}s")
                await asyncio.sleep(e.value)
        
        total_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Delete status message
        await status_message.delete()
        
        # Update stats
        stats["total_processed"] += 1
        bytes_saved = original_info["size_bytes"] - processed_info["size_bytes"]
        if bytes_saved > 0:
            stats["total_bytes_saved"] += bytes_saved
        
        logger.info(
            f"Completed: {original_name} -> {output_filename} "
            f"({original_info['size_mb']}MB -> {processed_info['size_mb']}MB) "
            f"in {total_time:.1f}s"
        )
        
    except Exception as e:
        logger.error(f"Error processing {original_name}: {e}", exc_info=True)
        await status_message.edit_text(
            f"**❌ Error processing file**\n\n"
            f"Error: {str(e)}\n\n"
            "Please try again."
        )
    
    finally:
        # Cleanup
        processing_files.discard(file_id)
        
        for path in [input_path, output_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


def run_bot():
    """Run the bot."""
    logger.info("Starting PDF Bot...")
    app.run()


if __name__ == "__main__":
    run_bot()

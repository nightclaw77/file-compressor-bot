#!/usr/bin/env python3
"""
File Compressor Bot for Telegram
Compresses files to zip/rar and can merge multiple files into one archive.
"""

import os
import zipfile
import rarfile
import subprocess
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DOWNLOAD_DIR = "/tmp/compressor_bot/"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "📦 File Compressor Bot\n\n"
        "Send me files and I'll compress them!\n\n"
        "Commands:\n"
        "/zip - Compress to ZIP\n"
        "/rar - Compress to RAR\n"
        "/merge - Merge multiple files into one archive\n"
        "/help - Show help"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        "📦 File Compressor Bot\n\n"
        "1. Send me a file → I'll compress it to ZIP\n"
        "2. Send /zip before sending files → Compress to ZIP\n"
        "3. Send /rar before sending files → Compress to RAR\n"
        "4. Send multiple files then /merge → Merge into one archive\n\n"
        "Reply to a file with /compress to compress it."
    )

async def zip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set mode to ZIP"""
    context.user_data['compress_mode'] = 'zip'
    await update.message.reply_text("📇 Mode set to ZIP. Send me files!")

async def rar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set mode to RAR"""
    context.user_data['compress_mode'] = 'rar'
    await update.message.reply_text("📦 Mode set to RAR. Send me files!")

async def merge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable merge mode"""
    context.user_data['merge_mode'] = True
    context.user_data['merge_files'] = []
    await update.message.reply_text("🔀 Merge mode! Send multiple files, then reply with /done to merge them.")

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish merge and create archive"""
    if 'merge_files' not in context.user_data or not context.user_data['merge_files']:
        await update.message.reply_text("No files to merge!")
        return
    
    await update.message.reply_text("🔄 Creating archive...")
    
    user_id = update.effective_user.id
    output_name = f"merged_{user_id}"
    files = context.user_data['merge_files']
    
    try:
        # Create ZIP
        output_path = f"{DOWNLOAD_DIR}{output_name}.zip"
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in files:
                zipf.write(f, os.path.basename(f))
        
        # Send file
        await update.message.reply_document(document=open(output_path, 'rb'))
        await update.message.reply_text("✅ Done!")
        
        # Cleanup
        for f in files:
            os.remove(f)
        os.remove(output_path)
        context.user_data['merge_files'] = []
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming documents"""
    document = update.message.document
    if not document:
        return
    
    file = await context.bot.get_file(document.file_id)
    user_id = update.effective_user.id
    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{document.file_name}")
    
    await update.message.reply_text("📥 Downloading...")
    
    try:
        await file.download_to_drive(file_path)
        file_size = os.path.getsize(file_path)
        
        if file_size > MAX_FILE_SIZE:
            await update.message.reply_text(f"❌ File too big! Max: 50MB")
            os.remove(file_path)
            return
        
        # Check mode
        if context.user_data.get('merge_mode'):
            context.user_data.setdefault('merge_files', []).append(file_path)
            await update.message.reply_text(
                f"✅ File added! ({len(context.user_data['merge_files'])} files)\n"
                "Send more files or /done to merge."
            )
            return
        
        compress_mode = context.user_data.get('compress_mode', 'zip')
        
        await update.message.reply_text(f"📦 Compressing to {compress_mode.upper()}...")
        
        if compress_mode == 'rar':
            output_path = file_path.replace(os.path.splitext(file_path)[1], '.rar')
            with rarfile.RarFile(output_path, 'w') as rarf:
                rarf.write(file_path, os.path.basename(file_path))
        else:
            output_path = file_path.replace(os.path.splitext(file_path)[1], '.zip')
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(file_path, os.path.basename(file_path))
        
        # Send compressed file
        await update.message.reply_document(document=open(output_path, 'rb'))
        
        # Cleanup
        os.remove(file_path)
        if output_path != file_path:
            os.remove(output_path)
        
        await update.message.reply_text("✅ Done!")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)

async def compress_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /compress reply"""
    if not update.message.reply_to_message:
        return
    
    if not update.message.reply_to_message.document:
        await update.message.reply_text("Reply to a document!")
        return
    
    # Process as document
    document = update.message.reply_to_message.document
    file = await context.bot.get_file(document.file_id)
    user_id = update.effective_user.id
    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{document.file_name}")
    
    await update.message.reply_text("📥 Downloading...")
    await file.download_to_drive(file_path)
    
    await update.message.reply_text("📦 Compressing...")
    
    output_path = file_path.replace(os.path.splitext(file_path)[1], '.zip')
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(file_path, os.path.basename(file_path))
    
    await update.message.reply_document(document=open(output_path, 'rb'))
    
    os.remove(file_path)
    os.remove(output_path)
    await update.message.reply_text("✅ Done!")

def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("zip", zip_command))
    application.add_handler(CommandHandler("rar", rar_command))
    application.add_handler(CommandHandler("merge", merge_command))
    application.add_handler(CommandHandler("done", done_command))
    application.add_handler(CommandHandler("compress", compress_reply))
    
    # Documents
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("🤖 Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

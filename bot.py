#!/usr/bin/env python3
"""
File Compressor Bot for Telegram
Compresses files to zip/rar and can merge multiple files into one archive.
"""

import os
import zipfile
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8761176747:AAHJUoC3FeCuj_v8v8qGg1MV-kE2V_cCst4")
DOWNLOAD_DIR = "/tmp/compressor_bot/"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Stylish menu keyboard
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📇 Compress to ZIP", callback_data="mode_zip")],
        [InlineKeyboardButton("📦 Compress to RAR", callback_data="mode_rar")],
        [InlineKeyboardButton("🔀 Merge Files", callback_data="mode_merge")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Welcome {user}!\n\n"
        "I'm your **File Compressor Bot** 📦\n\n"
        "I can help you:\n"
        "• 📇 Compress files to ZIP\n"
        "• 📦 Compress files to RAR\n"
        "• 🔀 Merge multiple files\n\n"
        "Choose an option:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        "📦 *File Compressor Bot*\n\n"
        "Choose an option from the menu below:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "mode_zip":
        context.user_data['compress_mode'] = 'zip'
        context.user_data['merge_mode'] = False
        context.user_data['merge_files'] = []
        await query.edit_message_text(
            "📇 *ZIP Mode Selected*\n\n"
            "Send me your files and I'll compress them to ZIP!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
            ]),
            parse_mode="Markdown"
        )
    elif query.data == "mode_rar":
        context.user_data['compress_mode'] = 'rar'
        context.user_data['merge_mode'] = False
        context.user_data['merge_files'] = []
        await query.edit_message_text(
            "📦 *RAR Mode Selected*\n\n"
            "Send me your files and I'll compress them to RAR!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
            ]),
            parse_mode="Markdown"
        )
    elif query.data == "mode_merge":
        context.user_data['merge_mode'] = True
        context.user_data['merge_files'] = []
        context.user_data['merge_filenames'] = []
        await query.edit_message_text(
            "🔀 *Merge Mode Selected*\n\n"
            "Send me multiple files, then tap /done when finished!\n\n"
            "The final archive will be named after your first file.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
            ]),
            parse_mode="Markdown"
        )
    elif query.data == "cancel":
        context.user_data.clear()
        await query.edit_message_text(
            "❌ *Cancelled*\n\n",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
    elif query.data == "back_menu":
        await query.edit_message_text(
            "📦 *File Compressor Bot*\n\n"
            "Choose an option:",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish merge and ask for caption"""
    if 'merge_files' not in context.user_data or not context.user_data['merge_files']:
        await update.message.reply_text("❌ No files to merge!")
        return
    
    # Get first filename for the archive name
    first_filename = context.user_data.get('merge_filenames', ['merged'])[0]
    base_name = os.path.splitext(first_filename)[0]
    context.user_data['archive_name'] = base_name
    
    # Ask for caption
    await update.message.reply_text(
        "📝 *Enter caption for the archive*\n\n"
        "Reply with your caption, or send /skip to continue without caption.",
        parse_mode="Markdown"
    )

async def skip_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip caption and create archive"""
    await create_and_send_archive(update, context, None)

async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle caption input"""
    caption = update.message.text
    if caption.startswith('/'):
        await create_and_send_archive(update, context, None)
    else:
        await create_and_send_archive(update, context, caption)

async def create_and_send_archive(update: Update, context: ContextTypes.DEFAULT_TYPE, caption: str = None):
    """Create and send the archive"""
    user_id = update.effective_user.id
    files = context.user_data.get('merge_files', [])
    
    if not files:
        await update.message.reply_text("❌ No files!", reply_markup=get_main_menu())
        return
    
    # Determine archive name
    if context.user_data.get('merge_mode'):
        base_name = context.user_data.get('archive_name', 'merged')
    else:
        # Single file - use original name
        base_name = os.path.splitext(os.path.basename(files[0]))[0]
    
    output_path = f"{DOWNLOAD_DIR}{base_name}.zip"
    
    # Update message with progress
    progress_msg = await update.message.reply_text(
        f"🔄 *Creating archive...*\n\n"
        f"Files: {len(files)}",
        parse_mode="Markdown"
    )
    
    try:
        # Create ZIP
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for i, f in enumerate(files):
                filename = os.path.basename(context.user_data.get('merge_filenames', [f]*len(files))[i])
                zipf.write(f, filename)
                await progress_msg.edit_text(
                    f"🔄 *Creating archive...*\n\n"
                    f"📁 Progress: {i+1}/{len(files)}\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"{'█' * ((i+1)*20//len(files))}{'░' * (20 - (i+1)*20//len(files))}",
                    parse_mode="Markdown"
                )
        
        # Send file with caption
        if caption:
            await progress_msg.edit_text(
                f"✅ *Done!*\n\n"
                f"📦 Archive: `{base_name}.zip`\n"
                f"📁 Files: {len(files)}",
                parse_mode="Markdown"
            )
            await update.message.reply_document(
                document=open(output_path, 'rb'),
                caption=f"📦 *{base_name}.zip*\n\n{caption}",
                parse_mode="Markdown"
            )
        else:
            await progress_msg.edit_text(
                f"✅ *Done!*\n\n"
                f"📦 Archive: `{base_name}.zip`\n"
                f"📁 Files: {len(files)}",
                parse_mode="Markdown"
            )
            await update.message.reply_document(document=open(output_path, 'rb'))
        
        # Cleanup
        for f in files:
            if os.path.exists(f):
                os.remove(f)
        os.remove(output_path)
        
        # Reset state
        context.user_data.clear()
        await update.message.reply_text(
            "🔄 Ready for more!",
            reply_markup=get_main_menu()
        )
        
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error: {str(e)}")
        context.user_data.clear()

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming documents"""
    document = update.message.document
    if not document:
        return
    
    file = await context.bot.get_file(document.file_id)
    user_id = update.effective_user.id
    original_filename = document.file_name
    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{document.file_id}_{original_filename}")
    
    # Send initial progress
    progress_msg = await update.message.reply_text(
        f"📥 *Downloading...*\n\n"
        f"📄 `{original_filename}`",
        parse_mode="Markdown"
    )
    
    try:
        await file.download_to_drive(file_path)
        file_size = os.path.getsize(file_path)
        
        if file_size > MAX_FILE_SIZE:
            await progress_msg.edit_text(
                f"❌ *File too big!*\n\n"
                f"Max size: 50MB\n"
                f"Your file: {file_size/1024/1024:.1f}MB",
                parse_mode="Markdown"
            )
            if os.path.exists(file_path):
                os.remove(file_path)
            return
        
        # Check mode
        if context.user_data.get('merge_mode'):
            context.user_data.setdefault('merge_files', []).append(file_path)
            context.user_data.setdefault('merge_filenames', []).append(original_filename)
            count = len(context.user_data['merge_files'])
            await progress_msg.edit_text(
                f"✅ *File added!*\n\n"
                f"📄 `{original_filename}`\n"
                f"📁 Total files: *{count}*\n\n"
                "Send more files or tap /done to merge.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Done - Create Archive", callback_data="done_merge")]
                ]),
                parse_mode="Markdown"
            )
            return
        
        compress_mode = context.user_data.get('compress_mode', 'zip')
        
        # Single file compression - keep original name
        base_name = os.path.splitext(original_filename)[0]
        
        await progress_msg.edit_text(
            f"📦 *Compressing...*\n\n"
            f"📄 `{original_filename}`\n"
            f"Format: {compress_mode.upper()}",
            parse_mode="Markdown"
        )
        
        if compress_mode == 'rar':
            output_path = file_path.replace(os.path.splitext(file_path)[1], '.rar')
            with rarfile.RarFile(output_path, 'w') as rarf:
                rarf.write(file_path, original_filename)
        else:
            output_path = file_path.replace(os.path.splitext(file_path)[1], '.zip')
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(file_path, original_filename)
        
        # Ask for caption
        context.user_data['pending_file'] = output_path
        context.user_data['pending_name'] = f"{base_name}.{'zip' if compress_mode == 'zip' else 'rar'}"
        
        await progress_msg.edit_text(
            f"✅ *Compressed!*\n\n"
            f"📦 `{base_name}.{'zip' if compress_mode == 'zip' else 'rar'}`\n\n"
            "📝 *Reply with caption* or /skip to send now.",
            parse_mode="Markdown"
        )
        
        # Cleanup original
        if os.path.exists(file_path):
            os.remove(file_path)
        
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)

async def done_merge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle done button in merge mode"""
    query = update.callback_query
    await query.answer()
    await done_command(update, context)

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip caption and send file"""
    if 'pending_file' in context.user_data:
        output_path = context.user_data.pop('pending_file')
        name = context.user_data.pop('pending_name')
        
        await update.message.reply_document(document=open(output_path, 'rb'))
        os.remove(output_path)
        
        await update.message.reply_text(
            "🔄 Ready for more!",
            reply_markup=get_main_menu()
        )
    else:
        await done_command(update, context)

def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("done", done_command))
    application.add_handler(CommandHandler("skip", skip_command))
    
    # Buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(CallbackQueryHandler(done_merge_callback, pattern="done_merge"))
    
    # Documents
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Caption handling for single files
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption))
    
    print("🤖 Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

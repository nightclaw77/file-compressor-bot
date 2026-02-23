#!/usr/bin/env python3
"""
File Compressor Bot for Telegram
Compresses files to zip/rar and can merge multiple files into one archive.
Stylish button interface!
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
ALLOWED_USERS = [971043547]  # Only these user IDs can use the bot

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Stylish menu keyboard with colors
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📇 Compress to ZIP", callback_data="mode_zip", style="primary")],
        [InlineKeyboardButton("📦 Compress to RAR", callback_data="mode_rar", style="primary")],
        [InlineKeyboardButton("🔀 Merge Files", callback_data="mode_merge", style="primary")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel", style="secondary")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_zip_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📇 Compress to ZIP", callback_data="mode_zip", style="primary")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu", style="secondary")],
    ])

def get_rar_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Compress to RAR", callback_data="mode_rar", style="primary")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu", style="secondary")],
    ])

def get_merge_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Done - Create Archive", callback_data="done_merge", style="primary")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu", style="secondary")],
    ])

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ This bot is private.")
        return
    
    user = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hey {user}! I'm your **File Compressor Bot** 📦\n\n"
        "I can compress your files to ZIP or RAR, or merge multiple files into one archive.\n\n"
        "Choose what you want to do:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if update.effective_user.id not in ALLOWED_USERS:
        return
    
    await update.message.reply_text(
        "📦 *File Compressor Bot*\n\n"
        "Choose what you want to do:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    if update.effective_user.id not in ALLOWED_USERS:
        await update.callback_query.answer("This bot is private.", show_alert=True)
        return
    
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "mode_zip":
        context.user_data['compress_mode'] = 'zip'
        context.user_data['merge_mode'] = False
        context.user_data['merge_files'] = []
        context.user_data['merge_filenames'] = []
        await query.edit_message_text(
            "📇 *ZIP Mode*\n\n"
            "Send me your files and I'll compress them to ZIP!",
            reply_markup=get_zip_menu(),
            parse_mode="Markdown"
        )
    elif query.data == "mode_rar":
        context.user_data['compress_mode'] = 'rar'
        context.user_data['merge_mode'] = False
        context.user_data['merge_files'] = []
        context.user_data['merge_filenames'] = []
        await query.edit_message_text(
            "📦 *RAR Mode*\n\n"
            "Send me your files and I'll compress them to RAR!",
            reply_markup=get_rar_menu(),
            parse_mode="Markdown"
        )
    elif query.data == "mode_merge":
        context.user_data['merge_mode'] = True
        context.user_data['merge_files'] = []
        context.user_data['merge_filenames'] = []
        await query.edit_message_text(
            "🔀 *Merge Mode*\n\n"
            "Send me multiple files, then tap **Done** when finished!\n\n"
            "The archive will be named after your first file.",
            reply_markup=get_merge_menu(),
            parse_mode="Markdown"
        )
    elif query.data == "cancel":
        context.user_data.clear()
        await query.edit_message_text(
            "❌ Cancelled",
            reply_markup=get_main_menu()
        )
    elif query.data == "back_menu":
        await query.edit_message_text(
            "📦 *File Compressor Bot*\n\n"
            "Choose what you want to do:",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
    elif query.data == "done_merge":
        await done_command(update, context)

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish merge and ask for caption"""
    if update.effective_user.id not in ALLOWED_USERS:
        return
    
    if 'merge_files' not in context.user_data or not context.user_data['merge_files']:
        await update.message.reply_text("❌ No files to merge!")
        return
    
    # Get first filename for the archive name
    first_filename = context.user_data.get('merge_filenames', ['merged'])[0]
    base_name = os.path.splitext(first_filename)[0]
    context.user_data['archive_name'] = base_name
    context.user_data['waiting_caption'] = True
    
    # Ask for caption
    await update.message.reply_text(
        "📝 *Enter caption*\n\n"
        "Reply with your caption, or send /skip to continue without caption.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ Skip", callback_data="skip_caption", style="secondary")]
        ])
    )

async def skip_caption_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip caption callback"""
    if update.effective_user.id not in ALLOWED_USERS:
        return
    
    query = update.callback_query
    await query.answer()
    await create_and_send_archive(update, context, None)

async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle caption input"""
    if update.effective_user.id not in ALLOWED_USERS:
        return
    
    if not context.user_data.get('waiting_caption'):
        return
    
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
    
    # Send initial progress
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
                
                # Calculate progress
                progress = (i + 1) / len(files)
                bars = int(progress * 20)
                progress_bar = "█" * bars + "░" * (20 - bars)
                
                await progress_msg.edit_text(
                    f"🔄 *Creating archive...*\n\n"
                    f"📁 Progress: {i+1}/{len(files)}\n"
                    f"```{progress_bar}```",
                    parse_mode="Markdown"
                )
        
        # Send file with caption
        if caption:
            await progress_msg.edit_text(
                f"✅ *Done!*\n\n"
                f"📦 `{base_name}.zip`\n"
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
                f"📦 `{base_name}.zip`\n"
                f"📁 Files: {len(files)}",
                parse_mode="Markdown"
            )
            await update.message.reply_document(document=open(output_path, 'rb'))
        
        # Show completion menu
        await update.message.reply_text(
            "🔄 Ready for more!",
            reply_markup=get_main_menu()
        )
        
        # Cleanup
        for f in files:
            if os.path.exists(f):
                os.remove(f)
        os.remove(output_path)
        
        # Reset state
        context.user_data.clear()
        
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error: {str(e)}")
        context.user_data.clear()

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming documents"""
    if update.effective_user.id not in ALLOWED_USERS:
        return
    
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
                f"📁 Total: *{count}* files",
                reply_markup=get_merge_menu(),
                parse_mode="Markdown"
            )
            return
        
        compress_mode = context.user_data.get('compress_mode', 'zip')
        
        # Single file - keep original name
        base_name = os.path.splitext(original_filename)[0]
        
        await progress_msg.edit_text(
            f"📦 *Compressing...*\n\n"
            f"📄 `{original_filename}`\n"
            f"Format: {compress_mode.upper()}",
            parse_mode="Markdown"
        )
        
        # Compress
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
        context.user_data['waiting_caption'] = True
        
        ext = 'zip' if compress_mode == 'zip' else 'rar'
        await progress_msg.edit_text(
            f"✅ *Compressed!*\n\n"
            f"📦 `{base_name}.{ext}`\n\n"
            "📝 *Reply with caption* or tap Skip.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭️ Skip", callback_data="skip_caption_single", style="secondary")]
            ]),
            parse_mode="Markdown"
        )
        
        # Cleanup original
        if os.path.exists(file_path):
            os.remove(file_path)
        
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)

async def skip_caption_single_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip caption for single file"""
    if update.effective_user.id not in ALLOWED_USERS:
        return
    
    query = update.callback_query
    await query.answer()
    
    output_path = context.user_data.pop('pending_file', None)
    name = context.user_data.pop('pending_name', 'archive')
    context.user_data.pop('waiting_caption', None)
    
    if output_path and os.path.exists(output_path):
        await update.message.reply_document(document=open(output_path, 'rb'))
        os.remove(output_path)
    
    await update.message.reply_text(
        "🔄 Ready for more!",
        reply_markup=get_main_menu()
    )

def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("done", done_command))
    application.add_handler(CommandHandler("skip", lambda u, c: create_and_send_archive(u, c, None)))
    
    # Buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    # done_merge handled in button_callback
    application.add_handler(CallbackQueryHandler(skip_caption_callback, pattern="skip_caption"))
    application.add_handler(CallbackQueryHandler(skip_caption_single_callback, pattern="skip_caption_single"))
    
    # Documents
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Caption handling
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption))
    
    print("🤖 Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

import os
import sys
import asyncio
import logging
import subprocess
import threading
from flask import Flask
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)

# --- [ CONFIG ] ---
TOKEN = "8650245274:AAHWHzDY4LcJzSs1P6yztQLnxFUcfOXOiSY"
ADMIN_ID = 7136887795
ACTIVE_FLEET = {}

# Fast Web Server
app = Flask('')
@app.route('/')
def home(): return "Core Fast"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

logging.basicConfig(level=logging.ERROR) # লগ কমিয়ে স্পিড বাড়ানো হয়েছে

# States
AUTH, DASHBOARD, UPLOAD_CODE, UPLOAD_REQ = range(4)

# --- [ FAST UI ] ---
def get_main_kb(user_id):
    btns = [
        [KeyboardButton("🚀 Deploy Bot"), KeyboardButton("🛰️ My Fleet")],
        [KeyboardButton("📊 Status"), KeyboardButton("⚙️ Support")]
    ]
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

# --- [ HANDLERS ] ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # সরাসরি ভেরিফিকেশন বাটন
    btn = [[KeyboardButton("🔐 Fast Verify", request_contact=True)]]
    await update.message.reply_text(
        "<b>⚡ NEXUS FAST HOSTING</b>\nভেরিফাই করতে কন্টাক্ট শেয়ার করুন।",
        reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True),
        parse_mode=ParseMode.HTML
    )
    return AUTH

async def auth_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ভেরিফিকেশন সাথে সাথে হবে, কোনো ওয়েট নেই
    if update.message.contact.user_id != update.message.from_user.id:
        await update.message.reply_text("❌ নিজের কন্টাক্ট দিন।")
        return AUTH
    
    # ড্যাশবোর্ড সরাসরি কল করা হয়েছে
    return await show_dashboard(update, context)

async def show_dashboard(update, context):
    user = update.effective_user
    await update.message.reply_text(
        f"<b>🚀 ড্যাশবোর্ড রেডি!</b>\nইউজার: <code>{user.first_name}</code>",
        reply_markup=get_main_kb(user.id),
        parse_mode=ParseMode.HTML
    )
    return DASHBOARD

async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🚀 Deploy Bot":
        await update.message.reply_text("📂 <b>bot.py</b> ফাইলটি দিন।", parse_mode=ParseMode.HTML)
        return UPLOAD_CODE
    elif text == "🛰️ My Fleet":
        return await my_fleet(update, context)
    elif text == "📊 Status":
        await update.message.reply_text("🟢 <b>Server:</b> Online\n⚡ <b>Speed:</b> Ultra Fast")
    return DASHBOARD

# --- [ REAL-TIME ENGINE (NON-BLOCKING) ] ---

async def my_fleet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    path = f"fleet/{user_id}"
    if not os.path.exists(f"{path}/bot.py"):
        await update.message.reply_text("❌ কোনো বট নেই।")
        return DASHBOARD

    status = "Online 🟢" if user_id in ACTIVE_FLEET else "Offline 🔴"
    btns = [[InlineKeyboardButton("⚡ Start", callback_query_data="run"),
             InlineKeyboardButton("🛑 Stop", callback_query_data="stop")],
            [InlineKeyboardButton("🗑️ Delete", callback_query_data="wipe")]]
    
    await update.message.reply_text(f"🤖 <b>Bot Manager</b>\nStatus: {status}", 
                                   reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
    return DASHBOARD

async def fleet_op(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    path = f"fleet/{user_id}"
    await query.answer()

    if query.data == "run":
        await query.edit_message_text("🚀 <b>Starting...</b>", parse_mode=ParseMode.HTML)
        # Non-blocking subprocess
        log_file = f"{path}/terminal.log"
        with open(log_file, "w") as f:
            proc = subprocess.Popen([sys.executable, f"{path}/bot.py"], stdout=f, stderr=f)
            ACTIVE_FLEET[user_id] = proc
        await query.edit_message_text("✅ <b>বট এখন লাইভ!</b>", parse_mode=ParseMode.HTML)

    elif query.data == "stop":
        if user_id in ACTIVE_FLEET:
            ACTIVE_FLEET[user_id].terminate()
            del ACTIVE_FLEET[user_id]
            await query.edit_message_text("🛑 বন্ধ করা হয়েছে।")

    elif query.data == "wipe":
        if user_id in ACTIVE_FLEET: ACTIVE_FLEET[user_id].terminate(); del ACTIVE_FLEET[user_id]
        import shutil
        shutil.rmtree(path, ignore_errors=True)
        await query.edit_message_text("🗑️ ডিলিট করা হয়েছে।")

# --- [ FILE HANDLERS ] ---

async def bot_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    os.makedirs(f"fleet/{user_id}", exist_ok=True)
    file = await context.bot.get_file(update.message.document.file_id)
    await file.download_to_drive(f"fleet/{user_id}/bot.py")
    await update.message.reply_text("✅ কোড সেভ হয়েছে। <b>requirements.txt</b> দিন (না থাকলে 'skip' লিখুন)।")
    return UPLOAD_REQ

async def req_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        await file.download_to_drive(f"fleet/{user_id}/requirements.txt")
    await update.message.reply_text("✅ রেডি!")
    return await show_dashboard(update, context)

# --- [ RUN ] ---

def main():
    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH: [MessageHandler(filters.CONTACT, auth_check)],
            DASHBOARD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dashboard),
                CallbackQueryHandler(fleet_op)
            ],
            UPLOAD_CODE: [MessageHandler(filters.Document.ALL, bot_rec)],
            UPLOAD_REQ: [MessageHandler(filters.Document.ALL | filters.Regex("(?i)skip"), req_rec)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()

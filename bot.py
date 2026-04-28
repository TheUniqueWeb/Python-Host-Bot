import os
import sys
import asyncio
import logging
import subprocess
import threading
import shutil
import psutil
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

# --- [ কনফিগারেশন ] ---
TOKEN = "8650245274:AAHWHzDY4LcJzSs1P6yztQLnxFUcfOXOiSY"
ADMIN_ID = 7136887795
ACTIVE_FLEET = {}

# --- [ RENDER WEB SERVER ] ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "NEXUS CORE IS LIVE 🟢", 200

def run_web():
    # Render সাধারণত 10000 পোর্ট ব্যবহার করে
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Logging
logging.basicConfig(level=logging.INFO)

# States
AUTH, DASHBOARD, UPLOAD_CODE, UPLOAD_REQ = range(4)

# --- [ UI HELPERS ] ---
def get_main_kb(user_id):
    btns = [
        [KeyboardButton("🚀 Deploy New Bot"), KeyboardButton("🛰️ My Fleet")],
        [KeyboardButton("📊 Analytics"), KeyboardButton("🛠️ Support")]
    ]
    if user_id == ADMIN_ID:
        btns.append([KeyboardButton("👑 Admin Panel")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

# --- [ HANDLERS ] ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"<b>💎 NEXUS CLOUD V4</b>\n\n"
        f"👋 স্বাগতম <b>{user.first_name}</b>!\n"
        f"ভেরিফাই করতে কন্টাক্ট শেয়ার করুন।"
    )
    btn = [[KeyboardButton("🔐 Verify Account", request_contact=True)]]
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return AUTH

async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact.user_id != update.message.from_user.id:
        return AUTH
    await update.message.reply_text("✅ ভেরিফিকেশন সফল!", reply_markup=ReplyKeyboardRemove())
    return await show_dash(update, context)

async def show_dash(update, context):
    user = update.effective_user
    text = f"<b>🖥️ DASHBOARD</b>\n👤 User: <code>{user.first_name}</code>\n📡 Status: <code>Active 🟢</code>"
    await update.message.reply_text(text, reply_markup=get_main_kb(user.id), parse_mode=ParseMode.HTML)
    return DASHBOARD

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🚀 Deploy New Bot":
        await update.message.reply_text("📂 আপনার <b>bot.py</b> ফাইলটি পাঠান।", parse_mode=ParseMode.HTML)
        return UPLOAD_CODE
    elif text == "🛰️ My Fleet":
        return await my_fleet(update, context)
    elif text == "📊 Analytics":
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        await update.message.reply_text(f"📊 <b>SERVER STATS</b>\n\nCPU: {cpu}%\nRAM: {ram}%", parse_mode=ParseMode.HTML)
    return DASHBOARD

# --- [ FLEET MANAGER ] ---
async def my_fleet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    path = f"fleet/{user_id}"
    if not os.path.exists(f"{path}/bot.py"):
        await update.message.reply_text("❌ কোনো বট নেই।")
        return DASHBOARD
    
    status = "Online 🟢" if user_id in ACTIVE_FLEET else "Offline 🔴"
    btns = [[InlineKeyboardButton("⚡ Start", callback_query_data="run"),
             InlineKeyboardButton("🛑 Stop", callback_query_data="stop")],
            [InlineKeyboardButton("📜 Logs", callback_query_data="logs"),
             InlineKeyboardButton("🗑️ Wipe", callback_query_data="wipe")]]
    
    await update.message.reply_text(f"🤖 <b>Bot Manager</b>\nStatus: {status}", 
                                   reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)
    return DASHBOARD

async def fleet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    path = f"fleet/{user_id}"
    await query.answer()

    if query.data == "run":
        if user_id in ACTIVE_FLEET: ACTIVE_FLEET[user_id].terminate()
        log_file = f"{path}/terminal.log"
        with open(log_file, "w") as f:
            proc = subprocess.Popen([sys.executable, f"{path}/bot.py"], stdout=f, stderr=f)
            ACTIVE_FLEET[user_id] = proc
        await query.edit_message_text("🚀 বট লাইভ হয়েছে!")
    elif query.data == "stop":
        if user_id in ACTIVE_FLEET:
            ACTIVE_FLEET[user_id].terminate()
            del ACTIVE_FLEET[user_id]
        await query.edit_message_text("🛑 বন্ধ করা হয়েছে।")
    elif query.data == "logs":
        if os.path.exists(f"{path}/terminal.log"):
            with open(f"{path}/terminal.log", "r") as f: logs = f.read()[-500:]
            await query.message.reply_text(f"📜 <b>Logs:</b>\n<code>{logs}</code>", parse_mode=ParseMode.HTML)
    elif query.data == "wipe":
        shutil.rmtree(path, ignore_errors=True)
        await query.edit_message_text("🗑️ ডিলিট করা হয়েছে।")

# --- [ FILE RECEIVERS ] ---
async def bot_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    os.makedirs(f"fleet/{user_id}", exist_ok=True)
    file = await context.bot.get_file(update.message.document.file_id)
    await file.download_to_drive(f"fleet/{user_id}/bot.py")
    await update.message.reply_text("✅ Code Saved! requirements.txt দিন (বা skip লিখুন)।")
    return UPLOAD_REQ

async def req_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        await file.download_to_drive(f"fleet/{user_id}/requirements.txt")
    await update.message.reply_text("✅ Setup Complete!")
    return await show_dash(update, context)

# --- [ MAIN ] ---
def main():
    # ১. ওয়েব সার্ভার ব্যাকগ্রাউন্ডে চালু করা (Render-এর জন্য)
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    # ২. টেলিগ্রাম বট চালু করা
    application = Application.builder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH: [MessageHandler(filters.CONTACT, auth_handler)],
            DASHBOARD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu),
                CallbackQueryHandler(fleet_callback)
            ],
            UPLOAD_CODE: [MessageHandler(filters.Document.ALL, bot_rec)],
            UPLOAD_REQ: [MessageHandler(filters.Document.ALL | filters.Regex("(?i)skip"), req_rec)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    application.add_handler(conv)
    print("🚀 Master Bot is Starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
